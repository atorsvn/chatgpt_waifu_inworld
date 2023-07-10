import os
import json
import quart
import quart_cors
from quart import request
from avatar import AvatarRig  # Assuming AvatarRig class is in the avatar.py file

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

rig = AvatarRig('config/config.json')

@app.post("/create_avatar")
async def create_avatar():
    request_data = await request.get_json(force=True)
    query = request_data.get('query', '')
    user_name = request_data.get('user_name', '')
    channel_id = request_data.get('channel_id', '')
    user_id = request_data.get('user_id', '')

    rig.chat_query(query, user_name, channel_id, user_id)
    result = rig.create_avatar_video()

    # Split the gif path to get only the file name
    gif_file_name = os.path.basename(json.loads(result)['gif_file'])

    return quart.Response(response=json.dumps({
        'chat_text': json.loads(result)['chat_text'],
        'gif_file': gif_file_name
    }), status=200)

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")

@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
