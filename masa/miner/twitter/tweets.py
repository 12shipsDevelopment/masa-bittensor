import bittensor as bt
import requests
from typing import List, Optional
from masa.miner.masa_protocol_request import MasaProtocolRequest
from masa.types.twitter import ProtocolTwitterTweetResponse
from masa.synapses import RecentTweetsSynapse


def handle_recent_tweets(
    synapse: RecentTweetsSynapse, max: int, caller_uid: int, miner_uid: int
) -> RecentTweetsSynapse:
    synapse.response = TwitterTweetsRequest(max).get_recent_tweets(
        synapse, caller_uid, miner_uid
    )
    return synapse


class TwitterTweetsRequest(MasaProtocolRequest):
    def __init__(self, max_tweets: int):
        super().__init__()
        # note, the max is determined by the miner config --twitter.max_tweets_per_request
        self.max_tweets = max_tweets

    def get_recent_tweets(
        self, synapse: RecentTweetsSynapse, caller_uid: int, miner_uid: int
    ) -> Optional[List[ProtocolTwitterTweetResponse]]:
        bt.logging.info(
            f"Getting {synapse.count} recent tweets for: {synapse.query}"
        )
        bt.logging.info(
            f"Getting {synapse.count or self.max_tweets} recent tweets for: {synapse.query}"
        )

        try:
            response = self.post(
                "/data/twitter/tweets/recent",
                body={
                    "query": synapse.query,
                    "count": synapse.count or self.max_tweets,
                    "caller_uid": caller_uid,
                    "miner_uid": miner_uid,
                },
                timeout=synapse.timeout,
            )
            if response.ok:
                data = self.format(response)
                bt.logging.success(
                    f"[monitor] {synapse.query} Sending {len(data)} tweets to validator {caller_uid}..."
                )
                return data
            else:
                f"[monitor] {synapse.query} from {caller_uid} Recent tweets request failed with status code: {response.status_code}"
        except requests.exceptions.RequestException as e:
            bt.logging.error(
                f"[monitor] {synapse.query} from {caller_uid} Recent tweets request failed: {e}"
            )
