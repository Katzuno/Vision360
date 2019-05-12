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
FACE_FOLDER = 'faces/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
OBJECTS_HEIGHT = {
	'laptop' : 30,
	'person' : 175,
	'bottle' : 20,
	'table' : 90,
	'chair' : 110,
	'phone' : 15,
	'paper' : 11,
	'mouse' : 5,
	'glasses' : 5,
	'sunglasses' : 6,
	'jeans' : 60,
	'man' : 180,
	'woman' : 160,
	'desk' : 110
}

app = Flask(__name__, static_url_path='')

app.config['IMG_FOLDER'] = IMG_FOLDER
app.config['AUDIO_FOLDER'] = AUDIO_FOLDER
app.config['FACE_FOLDER'] = FACE_FOLDER

CORS(app)

# Replace <Subscription Key> with your valid subscription key.
subscription_key_cv = "312eab3b151b4ba2bfc07e92fb0dd49b"
subscription_key_t2s = "da482cf4bb1f4c1784fe12b12ff81d88"
subscription_key_face = "ef5412a138bc4249b5362ae366f20108"
assert subscription_key_cv
assert subscription_key_t2s
assert subscription_key_face

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
face_api_url = 'https://francecentral.api.cognitive.microsoft.com/face/v1.0/'
face_detect_url = face_api_url + "detect"
face_verify_url = face_api_url + "verify" \
                                 ""
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
    return json.dumps({'url': redirect_uri, 'Status': 'File uploaded succesfully', 'Status_code': 1})

@app.route('/api/upload/face', methods=['POST'])
def upload_face():
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
        file.save(os.path.join(app.config['FACE_FOLDER'], filename))
        redirect_uri = request.host_url + "api/face?img_url=" + filename
    else:
        return json.dumps({'Status': 'Unexpected fail', 'Status_code': 0})
    return json.dumps({'url': redirect_uri, 'Status': 'File uploaded succesfully', 'Status_code': 1})

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
        desc = object['object']
        if desc in OBJECTS_HEIGHT.keys():
            real_height = OBJECTS_HEIGHT[desc.lower()]
        else:
            real_height = 15
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
    #return json.dumps(response.json())
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

@app.route('/api/face', methods=['GET'])
def face_recognition():
    if request.args.get('img_url'):
        image_url = app.config['FACE_FOLDER'] + request.args.get('img_url')
    else:
        return json.dumps({"Error": "Img_url is missing"})

    known_faces = [{'faceId': 'de71b4ae-4f2f-4853-9e62-9736d92cc3e8',
                    'name': 'dinca'},
                   {'faceId': '4f6821ee-3bab-4cf7-952b-158a69894e5a',
                    'name': 'narcis'},
                   {'faceId': 'f5579aa3-0f54-49a7-8ccf-b63e25a44d39',
                    'name': 'erik'},
                   ]
    image_data = open(image_url, "rb").read()

    headers = {'Ocp-Apim-Subscription-Key': subscription_key_face,
               'Content-Type': 'application/octet-stream'}

    params = {
        'returnFaceId': 'true',
        'returnFaceLandmarks': 'false',
        'returnFaceAttributes': '',
    }

    response = requests.post(face_detect_url, params=params, headers=headers, data=image_data)
    curr_face_id = response.json()[0]['faceId']
    headers = {'Ocp-Apim-Subscription-Key': subscription_key_face,
               'Content-Type': 'application/json'}

    index = 0
    identical = False
    while index < len(known_faces):
        params_verify = json.dumps({
            'faceId1': curr_face_id,
            'faceId2': known_faces[index]['faceId']
        }
        )
        response_verify = requests.post(face_verify_url, data=params_verify, headers=headers)
        resp_dict = response_verify.json()
        if resp_dict['isIdentical'] == True:
            identical = True
            break
        index = index + 1
    if identical == True:
        person_name = known_faces[index]['name'].title()
    else:
        person_name = 'Stranger'
    return json.dumps({'Identical': identical, 'Name': person_name})

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
    app.run("0.0.0.0", 8000)
