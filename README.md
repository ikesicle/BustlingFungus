# BustlingFungus
![Bustling Fungus](icon.png)  
A Discord bot which streams audio from Youtube to a Discord VC, made in the spirit of the now-deprecated Groovy bot. Supports shuffling, looping, and primitive searching on Youtube. Also supports radio streaming from `aac` audio streams via the `radio` command.  
To run it yourself, install Python 3.9.6 and install the required modules using `pip install -r requirements.txt`. You must also include the following files in the directory:

`config.json`:
```
{
    "token": [[[ Discord Bot Token Here ]]],
    "servicefile": [[[ Path to Service File ]]]
}
```
`servicefile.json`: A [Google Cloud Service Account Key](https://cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys) JSON file.
`stations.json` (optional): A JSON file containing the radio stations accessible via `radio`. The key of an entry is the name which invokes the station, and the entry itself contains `name` and `url` for the actual name of the station and the audio stream associated with it. Example:
```
{
    "jazz": {
        "name": "Jazz Radio",
        "url": "https://sample.jazzradio.com/stream"
    }
}
```
An associated thumbnail for the station can also be included in the `image` directory.
