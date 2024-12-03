# The MIT License (MIT)
# Copyright © 2023 Yuma Rao

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import copy
from abc import ABC
import bittensor as bt
import subprocess
import requests
from dotenv import load_dotenv
from masa_ai.tools.validator import TrendingQueries
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse
from masa.synapses import RecentTweetsSynapse
from typing import List, Optional
import random
import json

# Sync calls set weights and also resyncs the metagraph.
from masa.utils.config import check_config, add_args, config
from masa.utils.misc import ttl_get_block
from masa import __spec_version__ as spec_version

# Load the .env file for each neuron that tries to run the code
load_dotenv()


class ScrapeTwitter(MasaProtocolRequest):
    def __init__(self):
        super().__init__()

    def get_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Optional[List[ProtocolTwitterTweetResponse]]:
        bt.logging.info(f"Scraping {synapse.count} recent tweets for: {synapse.query}")
        try:
            response = self.post(
                "/data/twitter/tweets/recent",
                body={
                    "query": synapse.query,
                    "count": synapse.count,
                },
                timeout=synapse.timeout,
            )
            if response.ok:
                data = self.format(response)
                bt.logging.success(f"Scraped {len(data)} tweets...")
                return data
            else:
                bt.logging.error(
                    f"Recent tweets request failed with status code: {response.status_code}"
                )
        except requests.exceptions.RequestException as e:
            bt.logging.error(f"Recent tweets request failed: {e}")


class BaseNeuron(ABC):
    """
    Base class for Bittensor miners. This class is abstract and should be inherited by a subclass. It contains the core logic for all neurons; validators and miners.

    In addition to creating a wallet, subtensor, and metagraph, this class also handles the synchronization of the network state via a basic checkpointing mechanism based on epoch length.
    """

    neuron_type: str = "BaseNeuron"

    @classmethod
    def check_config(cls, config: "bt.Config"):
        check_config(cls, config)

    @classmethod
    def add_args(cls, parser):
        add_args(cls, parser)

    @classmethod
    def config(cls):
        return config(cls)

    subtensor: "bt.subtensor"
    wallet: "bt.wallet"
    metagraph: "bt.metagraph"
    spec_version: int = spec_version

    @property
    def block(self):
        return ttl_get_block(self)

    def __init__(self, config=None):
        base_config = copy.deepcopy(config or BaseNeuron.config())
        self.config = self.config()
        self.config.merge(base_config)
        self.check_config(self.config)

        # Set up logging with the provided configuration and directory.
        bt.logging(
            config=self.config,
            logging_dir=self.config.full_path,
            debug=self.config.neuron.debug,
        )

        # If a gpu is required, set the device to cuda:N (e.g. cuda:0)
        self.device = self.config.neuron.device

        # Log the configuration for reference.
        bt.logging.info(self.config)

        # Build Bittensor objects
        # These are core Bittensor classes to interact with the network.
        bt.logging.info("Setting up bittensor objects.")

        self.wallet = bt.wallet(config=self.config)
        self.subtensor = bt.subtensor(config=self.config)
        self.metagraph = self.subtensor.metagraph(self.config.netuid)

        bt.logging.info(f"Wallet: {self.wallet}")
        bt.logging.info(f"Subtensor: {self.subtensor}")
        bt.logging.info(f"Metagraph: {self.metagraph}")

        # Check if the miner is registered on the Bittensor network before proceeding further.
        self.check_registered()

        # Check code version.  If version is less than weights_version, warn the user.
        weights_version = self.subtensor.get_subnet_hyperparameters(
            self.config.netuid
        ).weights_version
        if self.spec_version < weights_version:
            bt.logging.warning(
                f"🟡 Code is outdated based on subnet requirements!  Required: {weights_version}, Current: {self.spec_version}.  Please update your code to the latest release!"
            )
        else:
            bt.logging.success(f"🟢 Code is up to date based on subnet requirements!")

        # Each miner gets a unique identity (UID) in the network for differentiation.
        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
        bt.logging.info(
            f"Running neuron on subnet: {self.config.netuid} with uid {self.uid} using network: {self.subtensor.chain_endpoint}"
        )
        self.step = 0
        self.queries = []

    def sync(self):
        """
        Wrapper for synchronizing the state of the network for the given miner or validator.
        """
        # Ensure miner or validator hotkey is still registered on the network.
        self.check_registered()

        if self.should_sync_metagraph():
            self.resync_metagraph()

        if self.should_set_weights():
            try:
                self.set_weights()
            except Exception as e:
                bt.logging.error(f"Setting weights failed: {e}")

    def check_registered(self):
        # --- Check for registration.
        if not self.subtensor.is_hotkey_registered(
            netuid=self.config.netuid,
            hotkey_ss58=self.wallet.hotkey.ss58_address,
        ):
            bt.logging.error(
                f"Wallet: {self.wallet} is not registered on netuid {self.config.netuid}."
                f" Please register the hotkey using `btcli subnets register` before trying again"
            )
            exit()

    def should_sync_metagraph(self):
        """
        Check if enough epoch blocks have elapsed since the last checkpoint to sync.
        """
        return (
            self.block - self.metagraph.last_update[self.uid]
        ) > self.config.neuron.epoch_length

    def should_set_weights(self) -> bool:
        # Don't set weights on initialization.
        if self.step == 0:
            return False

        # Check if enough epoch blocks have elapsed since the last epoch.
        if self.config.neuron.disable_set_weights:
            return False

        # Define appropriate logic for when set weights.
        return (
            self.block - self.metagraph.last_update[self.uid]
        ) > self.config.neuron.epoch_length and self.neuron_type != "MinerNeuron"  # don't set weights if you're a miner

    def auto_update(self):
        trending_queries = TrendingQueries().fetch()
        self.queries = [query["query"] for query in trending_queries[:10]]

    async def scrape(self):
        # this function needs to scrape trends from the twitter API
        if not self.queries:
            self.auto_update()

        query = random.choice(self.queries)
        file_path = f"{query}.json"
        # load stored tweets...
        try:
            with open(file_path, "r") as json_file:
                stored_tweets = json.load(json_file)
            bt.logging.info(f"loaded {len(stored_tweets)} tweets from {file_path}...")
        except FileNotFoundError:
            bt.logging.warning(f"no existing file for {file_path}...")
            stored_tweets = []

        synapse = RecentTweetsSynapse(
            query=query, count=self.config.twitter.max_tweets_per_request, timeout=40
        )
        tweets = ScrapeTwitter().get_recent_tweets(synapse)
        if tweets:
            bt.logging.info(f"Scraped {len(tweets)} tweets for query: {query}")
            # add unique tweets to stored tweets...
            existing_ids = {tweet["Tweet"]["ID"] for tweet in stored_tweets}
            new_tweets = [
                tweet for tweet in tweets if tweet["Tweet"]["ID"] not in existing_ids
            ]
            bt.logging.info(f"adding {len(new_tweets)} new tweets to storage...")
            stored_tweets.extend(new_tweets)
            # save new tweets to json file...
            with open(file_path, "w") as json_file:
                json.dump(stored_tweets, json_file, indent=4)

        else:
            bt.logging.error(f"Failed to scrape tweets for query: {query}")
