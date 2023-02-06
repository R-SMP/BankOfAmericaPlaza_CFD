import json

with open('jsonpretty.json', 'r') as handle:
    parsed = json.load(handle)
    
print(json.dumps(parsed, indent=4))