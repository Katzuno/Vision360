from flask import Flask, request, redirect, url_for, send_from_directory, send_file
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
ocr_url = vision_base_url + "ocr"

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
        print({'Status': 'No selected file', 'Status_code': 0})
        return json.dumps({'Status': 'No selected file', 'Status_code': 0})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        print(file.filename)
        file.save(os.path.join(app.config['IMG_FOLDER'], filename))
        redirect_uri = request.host_url + "api/analyse?img_url=" + filename
    else:
        return json.dumps({'Status': 'Unexpected fail', 'Status_code': 0})
    return json.dumps({'url': redirect_uri, 'Status': 'File uploaded succesfully', 'Status_code': 0})


#http://backdoor.erikhenning.ro/etc/uploads2/IMG_20190511_132343.jpg
@app.route('/api/analyse', methods=['GET'])
def analyze_img():
    print("-------------REQUESTED ANALYZE IMAGE --------------------")
    # Set image_url to the URL of an image that you want to analyze.
    # img_url = image name
    if request.args.get('img_url'):
        image_url = app.config['IMG_FOLDER'] + request.args.get('img_url')
    else:
        return json.dumps({"Error": "Img_url is missing"})

    headers = {'Ocp-Apim-Subscription-Key': subscription_key_cv,
               'Content-Type': 'application/octet-stream'}
    params = {'visualFeatures': 'Objects'}
    image_data = open(image_url, "rb").read()
    # data = {'url': image_url}
    response = requests.post(analyze_url, headers=headers, params=params, data=image_data)
    response.raise_for_status()


    # The 'analysis' object contains various fields that describe the image. The most
    # relevant caption for the image is obtained from the 'description' property.
    analysis = response.json()

    object_list = []
    for object in analysis['objects']:
        obj_h = object['rectangle']['h']
        real_height = 15
        desc = object['object']
        obj = Object(obj_h, real_height, desc, object['rectangle'])
        obj.calculate_distance()
        object_list.append(obj)
    object_list = sorted(object_list, key=lambda k: k.distance)
    response_json = []
    for obj in object_list:
        print(str(obj))
        d = {'img_height': obj.img_height,
             'real_height': obj.real_height,
             'desc': obj.desc,
             'distance': obj.distance,
             'direction': get_directions(obj, image_url),
             'position': obj.position}
        response_json.append(d)
    print(response_json)
    return json.dumps(response_json)
#    image_caption = analysis

@app.route('/api/ocr', methods=['GET'])
def ocr_img():
    print("-------------REQUESTED ANALYZE IMAGE --------------------")
    # Set image_url to the URL of an image that you want to analyze.
    # img_url = image name
    if request.args.get('img_url'):
        image_url = app.config['IMG_FOLDER'] + request.args.get('img_url')
    else:
        return json.dumps({"Error": "Img_url is missing"})

    headers = {'Ocp-Apim-Subscription-Key': subscription_key_cv,
               'Content-Type': 'application/octet-stream'}
    params  = {'language': 'en'}
    image_data = open(image_url, "rb").read()
    # data = {'url': image_url}
    response = requests.post(ocr_url, headers=headers, params=params, data=image_data)
    response.raise_for_status()
    return json.dumps(response.json())
    analysis = response.json()
   # return json.dumps(analysis)
    # Extract the word bounding boxes and text.
    line_infos = [region["lines"] for region in analysis["regions"]]
    word_infos = []
    for line in line_infos:
        for word_metadata in line:
            for word_info in word_metadata["words"]:
                word_infos.append(word_info)

    content = []
    for word in word_infos:
        text = str(word["text"])
        content.append(text)
    return json.dumps(content)

# r = raza, coord = coordonata y obiectului
def in_range(coord, y, r):
    return abs(coord - y) <= r


def get_directions(object, image_url):
    # response = requests.get(image_url)
    img = Image.open(image_url)
    height, width = img.size
    cam_w, cam_h = width / 2, height
    x = object.position['x'] + object.position['w'] / 2
    y = object.position['y'] + object.position['h']
    direction = ""
    #print("===== DEBUG START =====", "\n", object.desc, " || Cam_w: ", cam_w, " | Cam_h: ", cam_h, " | X: ", x, " | Y: ", y)
    #print("===== DEBUG END ======")


    if in_range(x, cam_w, 100) and in_range(y, cam_h, 100):
        direction = "obstacle-front"
    elif not in_range(y, cam_h, 100) and in_range(x, cam_w, 100):
        direction = "front"
    elif x <= cam_w and y <= cam_h / 2:
        direction = "front-left"
    elif x >= cam_w and y <= cam_h / 2:
        direction = "front-right"
    elif x <= cam_w and y >= cam_h / 2:
        direction = "left"
    elif x >= cam_w and y >= cam_h / 2:
        direction = "right"
    else:
        direction = "NONE"

    """
    if in_range(x, mid_w, 150) and in_range(y, mid_w, 150):
        direction = "obstacle-front"
    elif in_range(y, mid_h, 100) and in_range(x, mid_h, 100):
        direction = "front"
    elif x <= mid_w and y <= mid_h:
        direction = "front-left"
    elif x >= mid_w and y <= mid_h:
        direction = "front-right"
    elif x <= mid_w and y >= mid_h:
        direction = "left" # immediate left
    elif x >= mid_w and y >= mid_h:
        direction = "right"
    """

    return direction


@app.route('/api/text-to-speech', methods=['GET'])
def text2speech():
    if request.args.get('text'):
        text = request.args.get('text')
    else:
        return json.dumps({"Error": "Text is missing"})
    tts_obj= TextToSpeech(subscription_key_t2s, text)
    tts_obj.get_token()
    path_to_file = tts_obj.save_audio()
    return send_file(
        path_to_file,
        mimetype="audio/wav",
        as_attachment=True,
        attachment_filename="audio.wav")


@app.route('/', methods=['GET'])
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run("gdcb.ro", 5000)
