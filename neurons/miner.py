# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# Copyright © 2023 Masa

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

import time
from typing import Any, Tuple
import bittensor as bt
import asyncio

from masa.base.miner import BaseMinerNeuron

from masa.synapses import (
    TwitterFollowersSynapse,
    TwitterProfileSynapse,
    RecentTweetsSynapse,
)


class Miner(BaseMinerNeuron):
    def __init__(self, config=None):
        super(Miner, self).__init__(config=config)
        self._is_initialized = False
        self.hotkeys = [
            "5G1NjW9YhXLadMWajvTkfcJy6up3yH2q1YzMXDTi6ijanChe",
            "5FFApaS75bv5pJHfAp2FVLBj9ZaXuFDjEypsaBNc1wCfe52v",
            "5F4tQyWrhfGVcNhoqeiNsR6KjD4wMZ2kfhLj4oHYuyHbZAc3",
            #"5EpkwChBsHyoKfBsEeZp58LgeMUByhrvBiNzeC99SaRuCL1V",
            "5CsvRJXuR955WojnGMdok1hbhffZyB4N5ocrv82f3p5A2zVp",
            "5GjuVigvCgxwgosBhJVzSnWv8YjYVLh6Gx6yuybtWbszpa97",
            "5Fy3MjrdKRvUWSuJa4Yd5dmBYunzKNmXnLcvP22NfaTvhQCY",
            "5F2CsUDVbRbVMXTh9fAzF9GacjVX7UapvRxidrxe7z8BYckQ",
            "5GazyN8PJNxGhX2mYDCHaEhawx8Cz9DDgup54j5RucWs9ELt",
            "5GazyN8PJNxGhX2mYDCHaEhawx8Cz9DDgup54j5RucWs9ELt",
            "5HbScNssaEfioJHXjcXdpyqo1AKnYjymidGF8opcF9rTFZdT",
            "5Gbdb5s2WrRaFXTgMUiVNBKACe3cgSLwZNyK2Vwvjfvf6jUJ"
        ]

    @classmethod
    async def create(cls, config=None):
        if config is None:
            config = cls.config()

        self = cls(config=config)
        await self.initialize(config)
        return self

    async def initialize(self, config=None):
        if self._is_initialized:
            return

        await super().initialize(config)
        bt.logging.info("Miner initialized with config: {}".format(config))
        self._is_initialized = True

    async def blacklist(self, synapse: Any) -> Tuple[bool, str]:
        # if await self.check_tempo(synapse):
        #     await self.check_stake(synapse)

        hotkey = synapse.dendrite.hotkey
        # uid = self.metagraph.hotkeys.index(hotkey)

        # bt.logging.trace(f"Neurons Staked: {self.neurons_permit_stake}")
        # bt.logging.trace(f"Validator Permit: {self.metagraph.validator_permit[uid]}")

        bt.logging.info(f"Got request from {hotkey}...")
        if (
            hotkey not in self.hotkeys
        ):
            bt.logging.warning(f"Blacklisting un-registered hotkey {hotkey}")
            return True, "Unrecognized hotkey"

        # if (
        #     not self.config.blacklist.allow_non_registered
        #     and hotkey not in self.metagraph.hotkeys
        # ):
        #     bt.logging.warning(f"Blacklisting un-registered hotkey {hotkey}")
        #     return True, "Unrecognized hotkey"
        # if (
        #     self.config.blacklist.force_validator_permit
        #     and not self.metagraph.validator_permit[uid]
        # ):
        #     bt.logging.warning(
        #         f"Blacklisting a request from non-validator hotkey {hotkey}"
        #     )
        #     return True, "Non-validator hotkey"
        # if hotkey not in self.neurons_permit_stake.keys():
        #     bt.logging.warning(
        #         f"Blacklisting a request from neuron without enough staked: {hotkey}"
        #     )
        #     return True, "Non-staked neuron"

        bt.logging.trace(f"Not Blacklisting recognized hotkey {hotkey}")
        return False, "Hotkey recognized!"

    # async def check_stake(self, synapse: Any):
        # current_stakes = self.metagraph.S
        # hotkey = synapse.dendrite.hotkey
        # uid = self.metagraph.hotkeys.index(hotkey)

        # if current_stakes[uid] < self.min_stake_required:
        #     if hotkey in self.neurons_permit_stake.keys():
        #         del self.neurons_permit_stake[hotkey]
        #         bt.logging.info(
        #             f"Removed neuron {hotkey} from staked list due to insufficient stake."
        #         )
        # else:
        #     self.neurons_permit_stake[hotkey] = await self.block
        #     bt.logging.info(f"Added neuron {hotkey} to staked list.")

    # async def check_tempo(self, synapse: Any) -> bool:
        # hotkey = synapse.dendrite.hotkey
        # last_checked_block = self.neurons_permit_stake.get(hotkey)
        # if last_checked_block is None:
        #     bt.logging.info("There is no last checked block, starting tempo check...")
        #     return True

        # blocks_since_last_check = await self.block - last_checked_block

        # if blocks_since_last_check >= self.tempo:
        #     bt.logging.trace(
        #         f"A tempo has passed.  Blocks since last check: {blocks_since_last_check}"
        #     )
        #     return True
        # else:
        #     bt.logging.trace(
        #         f"Not yet a tempo since last check. Blocks since last check: {blocks_since_last_check}"
        #     )
        #     return False

    async def priority(self, synapse: Any) -> float:
        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(
            f"Prioritizing {synapse.dendrite.hotkey} with value: ", priority
        )
        return priority

    # blacklist wrappers
    async def blacklist_twitter_profile(
        self, synapse: TwitterProfileSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_twitter_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    async def blacklist_recent_tweets(
        self, synapse: RecentTweetsSynapse
    ) -> Tuple[bool, str]:
        return await self.blacklist(synapse)

    # priority wrappers
    async def priority_twitter_profile(self, synapse: TwitterProfileSynapse) -> float:
        return await self.priority(synapse)

    async def priority_twitter_followers(
        self, synapse: TwitterFollowersSynapse
    ) -> float:
        return await self.priority(synapse)

    async def priority_recent_tweets(self, synapse: RecentTweetsSynapse) -> float:
        return await self.priority(synapse)


async def main():
    miner = await Miner.create()
    await miner.run()


if __name__ == "__main__":
    asyncio.run(main())
