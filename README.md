# Install

## Prerequisites

-   Python >= 3.10
-   A Google API Key, see: https://console.cloud.google.com
-   Follow tutorial on how to create a JSON credentials file: https://docs.gspread.org/en/latest/oauth2.html#for-bots-using-service-account

### Windows

```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
# Paste api key to the api_key.txt file
echo "MY_API_KEY" > api_key.txt
```

### Linux

```bash
python -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
# Paste api key to the api_key.txt file
echo "MY_API_KEY" > api_key.txt
```

# Usage

3 arguments, all optional:

-   `--q {query}` Query string (ex: "booba type beat", <b>with quotes!</b>)
-   `--type {email,insta,other,all}` Specify what type of 'links' to print at the end, it saves all links regardless
-   `--max {25}` Number of videos to query (no guarantee on the number of videos received)

All together:

```
python main.py --q {query} --max {25} --type {email}
```

Examples:

```
python main.py --q "booba type beat"
python main.py --q "ninho type beat" --type insta
python main.py --q "lafeve omg" --type insta --max 5
```
