import requests, argparse
parser = argparse.ArgumentParser()
parser.add_argument('tag')
args = parser.parse_args()
result = requests.get(f"https://github.com/YPSH-DGC/YPSH/releases/download/{args.tag}/YPSH-python-3.py").text.strip()
epath = "ypsh-release.py"
with open(epath, mode='w', encoding='utf-8') as f:
    f.write(result)