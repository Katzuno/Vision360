from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import os
import requests
from objects import Object
from flask_cors import CORS
# If you are using a Jupyter notebook, uncomment the following line.
# %matplotlib inline
import matplotlib.pyplot as plt
import json
from PIL import Image
from io import BytesIO
from tts import TextToSpeech

IMG_FOLDER = 'images/'
AUDIO_FOLDER = 'audio/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__, static_url_path='')

app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
CORS(app)

# Replace <Subscription Key> with your valid subscription key.
subscription_key_cv = "312eab3b151b4ba2bfc07e92fb0dd49b"
subscription_key_t2s = "da482cf4bb1f4c1784fe12b12ff81d88"
assert subscription_key_cv
assert subscription_key_t2s

# You must use the same region in your REST call as you used to get your
# subscription keys. For example, if you got your subscription keys from
# westus, replace "westcentralus" in the URI below with "westus".
#
# Free trial subscription keys are generated in the "westus" region.
# If you use a free trial subscription key, you shouldn't need to change
# this region.
vision_base_url = "https://francecentral.api.cognitive.microsoft.com/vision/v2.0/"

analyze_url = vision_base_url + "analyze"

# Display the image and overlay it with the caption.
"""
image = Image.open(BytesIO(requests.get(image_url).content))
plt.imshow(image)
plt.axis("off")
_ = plt.title(image_caption, size="x-large", y=-0.1)
plt.show()
"""
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.after_request
def after_request(response):
    response.headers.add('Content-type', 'application/json')
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/img/<path:path>')
def send_js(path):
    return send_from_directory('images', path)

@app.route('/api/upload', methods=['POST'])
def upload_file():
    print("Request to upload file")
    # check if the post request has the file part
    if 'file' not in request.files:
        print({'Status': 'No file part'})
        return json.dumps({'Status': 'No file part'})
    file = request.files['file']
    # if user does not select file, browser also
    # submit a empty part without filename
    if file.filename == '':
        print({'Status': 'No selected file'})
        return json.dumps({'Status': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        print(file.filename)
        file.save(os.path.join(app.config['IMG_FOLDER'], filename))
        img_url = request.host_url + "img/" + filename
        print(img_url)
        redirect_uri = request.host_url + "api/analyse?img_url=" + img_url
    else:
        return json.dumps({'Status': 'Unexpected fail'})
    return json.dumps({'Analyze_url': redirect_uri, 'Status': 'File uploaded succesfully'})


#http://backdoor.erikhenning.ro/etc/uploads2/IMG_20190511_132343.jpg
@app.route('/api/analyse', methods=['GET'])
def analyze_img():
    print("-------------REQUESTED ANALYZE IMAGE --------------------")
    # Set image_url to the URL of an image that you want to analyze.
    if request.args.get('img_url'):
        image_url = request.args.get('img_url')
    else:
        return json.dumps({"Error": "Img_url is missing"})


    headers = {'Ocp-Apim-Subscription-Key': subscription_key_cv}
    params = {'visualFeatures': 'Objects'}
    data = {'url': image_url}
    response = requests.post(analyze_url, headers=headers, params=params, json=data)
    response.raise_for_status()


    # The 'analysis' object contains various fields that describe the image. The most
    # relevant caption for the image is obtained from the 'description' property.
    analysis = response.json()
    object_list = []
    for object in analysis['objects']:
        obj_h = object['rectangle']['h']
        real_height = 15
        desc = object['object']
        obj = Object(obj_h, real_height, desc)
        obj.calculate_distance()
        object_list.append(obj)

    object_list = sorted(object_list, key=lambda k: k.distance)
    for obj in object_list:
        print(str(obj))

    return json.dumps(analysis)
#    image_caption = analysis

#def get_directions(object):


"""
@app.route('/api/text-to-speech', methods=['GET'])
def text2speech():
    if request.args.get('text'):
        image_url = request.args.get('text')
    else:
        return json.dumps({"Error": "Text is missing"})
    tts_obj= TextToSpeech(subscription_key_t2s)
    tts_obj.get_token()
    tts_obj.save_audio()
"""

@app.route('/', methods=['GET'])
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run("gdcb.ro", 5000)
