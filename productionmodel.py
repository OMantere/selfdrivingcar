import time
import cv2
import numpy as np
from openvino.inference_engine import IENetwork, IEPlugin
import multiprocessing
from carpwm import CarControl

control = CarControl(40, 7, verbose=False)
control.start()

cc = 1.0
width = 900
height = 480
pp_cut = 210
DIM=(width, height)
K=np.array([[DIM[0]/2/cc, 0.0, DIM[0]/2], [0.0, DIM[1]/2/cc, (DIM[1])/2], [0.0, 0.0, 1.0]])
Dfish = np.array([[-0.09],[-0.13],[-0.0],[-0.0]])
D=np.array([-0.20, -0.03, 0.01, 0.0, -0.0])

h,w = DIM
fmap1, fmap2 = cv2.fisheye.initUndistortRectifyMap(K, Dfish, np.eye(3), K, DIM, cv2.CV_16SC2)
map1, map2 = cv2.initUndistortRectifyMap(K,D,None,K,DIM,5)
mmap1, mmap2 = map1, map2
fisheye=True
if fisheye:
    mmap1, mmap2 = fmap1, fmap2

IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_CHANNELS = 135, 450, 3
INPUT_SHAPE = (IMAGE_HEIGHT, IMAGE_WIDTH, IMAGE_CHANNELS)

mat = np.zeros((height, width, 3), dtype=np.uint8)
mat2 = np.zeros((height, width, 3), dtype=np.uint8)
smaller = np.zeros(INPUT_SHAPE, dtype=np.uint8)


def postprocess(img):
    return img[pp_cut:,:,:]

def read_img(img):
    mat[:, int(width/2-640/2):int(width/2+640/2), :] = img 
    return mat

def undistorted(img, fisheye=True):
    h,w = img.shape[:2]
    cv2.remap(img, mmap1, mmap2, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, dst=mat2)
    return mat2

def transform(img, undistort=False):
    img = cv2.flip(cv2.cvtColor(img, cv2.COLOR_BGR2RGB), -1) 
    t0 = time.time()
    if undistort:
        img = undistorted(img)
    #print("Undistort is: {}".format(time.time()-t0))
    return postprocess(img)

def resize(image):
    return cv2.resize(image, (IMAGE_WIDTH, IMAGE_HEIGHT), cv2.INTER_AREA)

def rgb2yuv(image):
    return cv2.cvtColor(image, cv2.COLOR_RGB2YUV)

def disp(img):
    plt.figure()
    plt.imshow(img)

def get_input(i):
    return read_img(image_paths[i])

def preprocess_input(img):
    return rgb2yuv(resize(transform(img, undistort=True)))

def read_action(fpath):
    return np.float32([float(x) for x in open(fpath, 'r').read().strip().split()])

def get_output(i):
    return read_action(action_paths[i])[1] - 0.5




q1 = multiprocessing.Queue(maxsize=1)


def push_loop():
    control.set_throttle(0.5)
    print("Initializing camera...")
    cap = cv2.VideoCapture(0)
    print("Camera initialized")
    cap.open(0)
    print("Camera started")

    plugin = IEPlugin(device = "MYRIAD")
    model_path = '/home/pi/IR_model3/IR_model3'
    net = IENetwork(model = '{}.xml'.format(model_path), weights = '{}.bin'.format(model_path))
    input_blob = next(iter(net.inputs))
    out_blob = next(iter(net.outputs))
    n, c, h, w = net.inputs[input_blob].shape
    prepimg = np.ndarray(shape=(n, c, h, w))
    print("Loading model...")
    exec_net = plugin.load(network=net)
    print("Model loaded")
    i = 0
    t0 = time.time()
    while True:
        control.set_throttle(0.65)
        if i % 10 == 0:
            now = time.time()
            print("FPS: {}".format(1.0/(now - t0)*10))
            t0 = now
        i +=1

        success, img = cap.read()
        if not success:
            print("Capture failed")
        else:
            read_img(img)
            im = preprocess_input(mat)
            #with open('testimg.jpg', 'wb') as f:
            #    f.write(cv2.imencode('.jpg', im)[1])
        #   q1.put(im)
            im = im.transpose((-1, 0, 1))
            prepimg[0, :, :, :] = im
            res = exec_net.infer(inputs={input_blob: prepimg})
            val = res[out_blob][0][0]
            control.set_steering_angle(2.8*(val) + 0.5)
            #set_fun(res[out_blob][0][0])
            #v.value = res[out_blob][0][0]



def pull_loop(v):
    plugin = IEPlugin(device = "MYRIAD")
    model_path = '/home/pi/IR_model4/IR_model4'
    net = IENetwork(model = '{}.xml'.format(model_path), weights = '{}.bin'.format(model_path))
    input_blob = next(iter(net.inputs))
    out_blob = next(iter(net.outputs))
    n, c, h, w = net.inputs[input_blob].shape
    prepimg = np.ndarray(shape=(n, c, h, w))
    print("Loading model...")
    exec_net = plugin.load(network=net)
    print("Model loaded")
    i = 0
    t0 = time.time()
    while True:
        if i % 10 == 0:
            now = time.time()
            print("FPS: {}".format(1.0/(now - t0)*10))
            t0 = now
        i +=1
        im = q1.get()
        im = im.transpose((-1, 0, 1))
        prepimg[0, :, :, :] = im
        res = exec_net.infer(inputs={input_blob: prepimg})
        #set_fun(res[out_blob][0][0])
        v.value = res[out_blob][0][0]


def dummy_fun(angle):
    print("Predicted angle: {}".format(angle))

if __name__ == "__main__":
    push_loop()
    p1 = multiprocessing.Process(target=push_loop)
    p2 = multiprocessing.Process(target=pull_loop, args=(dummy_fun,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
