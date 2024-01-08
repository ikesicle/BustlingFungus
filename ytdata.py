import os

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2 import service_account

scopes = ["https://www.googleapis.com/auth/youtube.force-ssl"]

class YoutubeQuerier:
    def __init__(self, filepath):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        # os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"

        # Get credentials and create an API client
        self.credentials = service_account.Credentials.from_service_account_file(
            filepath, 
            scopes=scopes
        )
        self.client = googleapiclient.discovery.build(
            api_service_name, api_version, credentials=self.credentials)

    def query(self, q):
        request = self.client.search().list(
            part="snippet",
            maxResults=1,
            regionCode="CA",
            q=q,
            type="video"
        )
        response = request.execute()
        return response["items"][0]["id"]["videoId"]

    def getVideoInfo(self, _id):
        request = self.videos().list(
            part="snippet",
            id=_id
        )
        response = request.execute()
        return response["items"][0]["snippet"]
