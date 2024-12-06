import sys
import os
import json
from datetime import datetime
import threading
import queue
import time
import subprocess
import shlex
from PIL import Image
import base64
import io


channel = None
if sys.version_info[0]<3:
    channel = os.fdopen(3, "r+")
else:
    channel = os.fdopen(3, "r+b", buffering=0)


class Msg(object):
    SEND = 'send'
    LOG = 'log'
    WARN = 'warn'
    ERROR = 'error'
    STATUS = 'status'

    def __init__(self, ctx, value, msgid):
        self.ctx = ctx
        self.value = value
        self.msgid = msgid

    def dumps(self):
        return json.dumps(vars(self)) + "\\n"

    @classmethod
    def loads(cls, json_string):
        return cls(**json.load(json_string))


class Node(object):
    def __init__(self, msgid, channel):
            self.__msgid = msgid
            self.__channel = channel

    def send(self, msg):
            msg = Msg(Msg.SEND, msg, self.__msgid)
            self.send_to_node(msg)

    def log(self, *args):
            msg = Msg(Msg.LOG, args, self.__msgid)
            self.send_to_node(msg)

    def warn(self, *args):
            msg = Msg(Msg.WARN, args, self.__msgid)
            self.send_to_node(msg)

    def error(self, *args):
            msg = Msg(Msg.ERROR, args, self.__msgid)
            self.send_to_node(msg)

    def status(self, *args):
            msg = Msg(Msg.STATUS, args, self.__msgid)
            self.send_to_node(msg)

    def send_to_node(self, msg):
            m = msg.dumps()
            if sys.version_info[0]>2:
                m = m.encode("utf-8")
            self.__channel.write(m)

class RTSVideoCapture:


    def __init__(self, name):
        self.cap = cv2.VideoCapture(name)

        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) #internal buffer will now store only 1 frames
        print("Initializing Queue in threading")
        self.q = queue.Queue()
        self.rt = queue.Queue()
        t = threading.Thread(target=self._reader)
        t.daemon = True
        t.start()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            #print("ret inside rtsvideocalpture",ret)

            if not ret:
                print('ret',ret)
                self.rt.put(ret)
         
                break
            if not self.q.empty():
                try:
                    self.q.get_nowait()   # discard previous (unprocessed) frame
                    self.rt.get_nowait()  # discard previous (unprocessed) return values
                    print("discarding previous unprocessed frame")
                except queue.Empty:
                    pass
            self.q.put(frame)
            self.rt.put(ret)


    def read(self):
        if self.q.empty():
            return None,None
        #print('rf',self.rt.get(),self.q.get())
        return self.rt.get(),self.q.get()


#tf=""
model=""
data_all=""
# comment out below line to enable tensorflow outputs
#os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
physical_devices = tf.config.experimental.list_physical_devices('GPU')
if physical_devices:
  # Create 2 virtual GPUs with 1GB memory each
  try:
    tf.config.set_logical_device_configuration(
        physical_devices[0],
        [tf.config.LogicalDeviceConfiguration(memory_limit=1024*1),
         tf.config.LogicalDeviceConfiguration(memory_limit=1024*1)])
    logical_gpus = tf.config.list_logical_devices('GPU')
    print(len(physical_devices), "Physical GPU,", len(logical_gpus), "Logical GPUs")
  except RuntimeError as e:
    # Virtual devices must be set before GPUs have been initialized
    print(e)
# if len(physical_devices) > 0:
#         tf.config.experimental.set_memory_growth(physical_devices[0], True)




import BoxDetectionImports.core.utils as utils
from BoxDetectionImports.core.yolov4 import filter_boxes
from tensorflow.python.saved_model import tag_constants
from BoxDetectionImports.core.config import cfg
import cv2
import numpy as np
import matplotlib.pyplot as plt
# deep sort imports
from BoxDetectionImports.deep_sort import preprocessing, nn_matching
from BoxDetectionImports.deep_sort.detection import Detection
from BoxDetectionImports.deep_sort.tracker import Tracker
from BoxDetectionImports.tools import generate_detections as gdet


###Convert darknet weight to tensorflow
def box_checkpoint_load():
    framework='tf'
    #weights_weapon= '/interplay_v2/public/private/weaponresource/checkpoints_weapon/yolo_weapon1711_best_416' 
    input_size= 416
    
    
    config_data1 = '''
#! /usr/bin/env python
# coding=utf-8
from easydict import EasyDict as edict


__C                           = edict()
# Consumers can get config by: from config import cfg

cfg                           = __C

# YOLO options
__C.YOLO                      = edict()

__C.YOLO.CLASSES              = "/interplay_v2/BoxDetectionImports/data/classes/obj.names"
__C.YOLO.ANCHORS              = [12,16, 19,36, 40,28, 36,75, 76,55, 72,146, 142,110, 192,243, 459,401]
__C.YOLO.ANCHORS_V3           = [10,13, 16,30, 33,23, 30,61, 62,45, 59,119, 116,90, 156,198, 373,326]
__C.YOLO.ANCHORS_TINY         = [23,27, 37,58, 81,82, 81,82, 135,169, 344,319]
__C.YOLO.STRIDES              = [8, 16, 32]
__C.YOLO.STRIDES_TINY         = [16, 32]
__C.YOLO.XYSCALE              = [1.2, 1.1, 1.05]
__C.YOLO.XYSCALE_TINY         = [1.05, 1.05]
__C.YOLO.ANCHOR_PER_SCALE     = 3
__C.YOLO.IOU_LOSS_THRESH      = 0.5


# Train options
__C.TRAIN                     = edict()

__C.TRAIN.ANNOT_PATH          = "./data/dataset/val2017.txt"
__C.TRAIN.BATCH_SIZE          = 2
# __C.TRAIN.INPUT_SIZE            = [320, 352, 384, 416, 448, 480, 512, 544, 576, 608]
__C.TRAIN.INPUT_SIZE          = 416
__C.TRAIN.DATA_AUG            = True
__C.TRAIN.LR_INIT             = 1e-3
__C.TRAIN.LR_END              = 1e-6
__C.TRAIN.WARMUP_EPOCHS       = 2
__C.TRAIN.FISRT_STAGE_EPOCHS    = 20
__C.TRAIN.SECOND_STAGE_EPOCHS   = 30



# TEST options
__C.TEST                      = edict()

__C.TEST.ANNOT_PATH           = "./data/dataset/val2017.txt"
__C.TEST.BATCH_SIZE           = 2
__C.TEST.INPUT_SIZE           = 416
__C.TEST.DATA_AUG             = False
__C.TEST.DECTECTED_IMAGE_PATH = "./data/detection/"
__C.TEST.SCORE_THRESHOLD      = 0.25
__C.TEST.IOU_THRESHOLD        = 0.5

    '''
         

    with open('/interplay_v2/object_detection_yolov4_imports/core/config.py', 'w+') as f:
            f.write(config_data1)
            f.flush()
            f.close()

    
    
    def convert_darknet_weights_to_tensorflow(input_size):
        
        #weights = '/interplay_v2/public/private/box_counting/yolo_box2_final.weights'
        weights = '/interplay_v2/public/private/box_counting/yolo_box_Nov10_final.weights'
        checkpoint_path = '/interplay_v2/public/private/box_counting/models/yolo_box_Nov10_final'
        
        cmd = '/home/miniconda/bin/python3.9 /interplay_v2/save_model.py --weights '+weights+' \
          --output '+checkpoint_path+' \
          --input_size '+str(input_size)+' \
          --model yolov4' 
          
        print('cmd',cmd)
        sys.stdout.flush()
        if not os.path.exists(checkpoint_path):
            output = subprocess.check_output(shlex.split(cmd))
            print('output',output)
            sys.stdout.flush()
            
        elif len(os.listdir(checkpoint_path)) == 0:
            output = subprocess.check_output(shlex.split(cmd)) 
            print('output',output)
            sys.stdout.flush()


    
        return checkpoint_path
    
    

    
    
    weights= convert_darknet_weights_to_tensorflow(input_size)  #checkpoint path
    
    saved_model_loaded = ''
    infer = ''
    interpreter = ''
    input_details = ''
    output_details = ''
    ########Load model#####
    print("loading model")
    if framework == 'tflite':
          interpreter = tf.lite.Interpreter(model_path=weights)
          interpreter.allocate_tensors()
          input_details = interpreter.get_input_details()
          output_details = interpreter.get_output_details()
          print(input_details)
          print(output_details)    
          print("loaded model")    
    else:
          saved_model_loaded = tf.saved_model.load(weights, tags=[tag_constants.SERVING])
          infer = saved_model_loaded.signatures['serving_default'] 
          
          print("loaded model")
    
    return saved_model_loaded, infer, interpreter,input_details, output_details



# initialize deep sort
print("tracking model loading")
framework = 'tf'
# weights = '/interplay_v2/public/private/box_counting/checkpoints/yolov4-832'
# size = 832
weights = '/interplay_v2/public/private/box_counting/models/yolo_box_Nov10_final'
input_size = 416
tiny = False
model = 'yolov4'
# output_format = 'XVID' #for mp4
output_format = 'vp80' #for webm

iou=0.5
score = 0.5
dont_show = False
info = False
count = True

max_cosine_distance = 0.4
nn_budget = None
nms_max_overlap = 1.0
model_filename = '/interplay_v2/public/private/box_counting/mars-small128.pb'
encoder = gdet.create_box_encoder(model_filename, batch_size=1)
# calculate cosine distance metric
metric = nn_matching.NearestNeighborDistanceMetric("cosine", max_cosine_distance, nn_budget)
# initialize tracker
# tracker = Tracker(metric,max_age=20)


      
                
saved_model_loaded, infer, interpreter,input_details, output_details = box_checkpoint_load()





def python_function(msg_py,msg_local_py,current_process,exp_process,completed_process,msg_passing):
        
        except_arr = []

        #from WeaponDetectionImports.core.inference_images_weapon import inference_images_weapon
        from tensorflow.compat.v1 import ConfigProto
        from tensorflow.compat.v1 import InteractiveSession

        config = ConfigProto()
        #config.gpu_options.allow_growth = True
        #config.gpu_options.per_process_gpu_memory_fraction=0.25
        session = InteractiveSession(config=config)
        #physical_devices = tf.config.experimental.list_physical_devices('GPU')
        # if len(physical_devices) > 0:
        #     tf.config.experimental.set_memory_growth(physical_devices[0], True)

        #print(physical_devices)
        #print('python function starts')

    
        # initialize tracker
        tracker = Tracker(metric,max_age=30)
        
        
        if msg_local_py is None:
            print("msg_local_py none")
            #requests.post('https://advai.interplay.iterate.ai/nextnode',data = "msg_local_py non")
        elif msg_local_py is not None:
            #msgid = msg_local_py["_msgid"]
            #node = Node(msgid, channel)
            ui=msg_local_py["payload"]
            print("msg_local_py[payload]:",ui)

            video_url = ui["video_link"]
            print('video URL:',video_url)

            video_ext =  ui["video_type"]
            print('video Type:',video_ext)

            video_friendly_name =  ui["friendly_name"]
            print('Friendly name:',video_friendly_name)

            video_original_name =  ui["file_original_name"]
            print('Original name:',video_original_name)
            
            should_store_frames =  ui["should_store_frames"]
            print('should_store_frames:',should_store_frames)

            #video_name1 = video_url.split('/')[-1]   #Oxford_Street_in_London.mp4
            #video_name = video_name1.split('.')[0]   #Oxford_Street_in_London
            video_name1 = video_friendly_name  #if needed add the extension
            video_name = video_friendly_name
            video_original_name = video_original_name.split('.')[0] #without ext

            print("incide child process")
            #GPUtil.showUtilization()
            #print("Within the multiprocessing python after gettung all the details")
            #requests.post('https://advai.interplay.iterate.ai/nextnode',data = "Within the multiprocessing python after gettung all the details")
            
            if ((video_ext=='rtsp') or (video_ext=='mjpeg')) and ((video_url =="") or (video_friendly_name=="")):  #validation
                if len(current_process) > 0:
                    exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                    exp_process.append(exception_pro[0])
                now = datetime.now()
                dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
                data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':'Video link or friendly name is blank!'}

                print('Exception in the current frame:',data1)
                except_arr.append(data1)
                msg_py['payload'] = except_arr    # this will be displayed in fronted using socket
                msg_passing.append(msg_py)
                #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)
                #node.send(msg_py)   #Node's Output
                return msg_py

                

            if ((video_ext=='mp4') or (video_ext=='webm')) and (video_friendly_name==""):  #validation
                print("Within the multiprocessing python within validating")
                if len(current_process) > 0:
                        exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                        exp_process.append(exception_pro[0])
                now = datetime.now()
                dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
                data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':'Friendly name is blank!'}

                print('Exception in the current frame:',data1)
                except_arr.append(data1)
                msg_py['payload'] = except_arr    # this will be displayed in fronted using socket
                msg_passing.append(msg_py)
                #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)
                #node.send(msg_py)   #Node's Output
                return msg_py
            #######BEGIN INFERENCE



            #For videos, inference and save full video. for RTSP streams save last 5 mins frames
            if (video_ext in ['mp4','webm']):
                video_path ='/interplay_v2/public/private/box_counting/videos/'+video_original_name+'_input.mp4'

            elif (video_ext in ['rtsp','mjpeg']):
                video_path = video_url
                

            print('Begin video capture now')
            #print(video_path)
            if (video_ext in ['mp4','webm']):
                try:
                    vid = cv2.VideoCapture(str(video_path))
                    print("video ",vid)
                except Exception as e:
                    print('Video Capture Exception:',e)
                    #node.warn("Video URL is not valid")
                    if len(current_process) > 0:
                        exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                        exp_process.append(exception_pro[0])
                    return msg_py
            elif (video_ext in ['rtsp','mjpeg']):
                try:
                    print("Within reading path")
                    vid = cv2.VideoCapture(str(video_path))  #to get height, width of the frame to save
                    vid_latest_rtsp = RTSVideoCapture(str(video_path))    #Read the latest frame from rtsp stream
                    #########This part is added for find whether the rtsp stream url is invalid
                    return_value, frame = vid.read()

                    if not return_value:
                        print("Stream URL is invalid")

                        now = datetime.now()
                        dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
                        data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':'Stream URL is invalid!'}

                        print('Exception in the current frame:',data1)
                        except_arr.append(data1)
                        msg_py['payload'] = except_arr    # this will be displayed in fronted using socket
                        #node.send(msg_py)   #Node's Output
                        msg_passing.append(msg_py)
                        vid.release()
                        if len(current_process) > 0:
                            exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                            exp_process.append(exception_pro[0])
                        vid.release()

                        #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)

                        return msg_py
                        #################
                except Exception as e:
                    print('Video Capture Exception:',e)
                    print("Stream URL is invalid")

                    now = datetime.now()
                    dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
                    data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':'Stream URL is invalid!'}
                    print('Exception in the current frame:',data1)
                    except_arr.append(data1)
                    msg_py['payload'] = except_arr    # this will be displayed in fronted using socket
                    #node.send(msg_py)   #Node's Output
                    msg_passing.append(msg_py)
                    vid.release()
                    #node.warn("Video URL is not valid")
                    if len(current_process) > 0:
                        exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                        exp_process.append(exception_pro[0])
                    return msg_py





            import os
            import shutil

            if os.path.exists('/interplay_v2/public/private/box_counting/'+video_name):
                    shutil.rmtree('/interplay_v2/public/private/box_counting/'+video_name)  #remove directory even it contains files inside
                    print(video_name+' folder exists. So deleted it')

            if not os.path.exists('/interplay_v2/public/private/box_counting/'+video_name):
                    os.makedirs('/interplay_v2/public/private/box_counting/'+video_name)
                    os.makedirs('/interplay_v2/public/private/box_counting/'+video_name+'/snapshot/')
                    print('Created '+video_name+' folder')

            out = None
            output = '/interplay_v2/public/private/box_counting/'+video_name+'/'+video_name+'_1.webm'
            output_frame_path = '/interplay_v2/public/private/box_counting/'+video_name+'/snapshot/Live2.jpg'
            
            '''
            if (video_ext in ['mp4','webm']):
                output_path = '/interplay_v2/public/private/box_counting/'+video_name+'/'+video_name+'_1.webm'
                if output_path :

                        # by default VideoCapture returns float instead of int
                        width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = int(vid.get(cv2.CAP_PROP_FPS))
                        codec = cv2.VideoWriter_fourcc(*output_format)
                        out = cv2.VideoWriter(output_path, codec, fps, (width, height))
                        # out = cv2.VideoWriter(output_path, codec, fps/5, (width, height))
            '''            
            if (video_ext in ['rtsp','mjpeg']):

                if should_store_frames == True :
                        output_path = '/interplay_v2/public/private/box_counting/'+video_name+'/'+video_name+'_1.webm'
                        print('output_path',output_path)
                        # by default VideoCapture returns float instead of int
                        width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = 1
                        codec = cv2.VideoWriter_fourcc(*output_format)
                        out = cv2.VideoWriter(output_path, codec, fps, (width, height))
                        vid.release()

            frame_num = 0
            cnt = 0
            countt=0  #used for total box count
            fps_p = 0
            try:
                # while video is running
                while True:
     

                        if (video_ext in ['mp4','webm']):

                            print("Reading video frame")
                            return_value, frame = vid.read()

                            if return_value:
                                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                #image = Image.fromarray(frame)
                            else:

                                if frame_num !=0:   # if video format issue frame_num will be 0. if >0 then it is coming after inference is completed
                                    #after inference completed do this
                                    data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':None}

                                    arr_comp = []
                                    arr_comp.append(data1)
                                    #print("arr_comp",arr_comp)
                                    msg_py['payload'] = arr_comp    # this will be displayed in fronted using socket
                                    msg_passing.append(msg_py)
                                    #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)
                                    #node.send(msg_py)
                                    
                                    print(current_process)
                                    if len(current_process) > 0:
                                        completed_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                                        completed_process.append(completed_pro[0])
                                        
                                    print("Ended video inference here")
                                    #break
                                    return msg_py
                                else: #if any exception in reading video when reading the frame go inside this elif
                                    if len(current_process) > 0:
                                        exception_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                                        exp_process.append(exception_pro[0])
                                    now = datetime.now()
                                    dt_string = now.strftime("%d-%m-%Y %H:%M:%S")
                                    data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':None,'Track_id':None,'snapshot':None,'output_video_path':None,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None,'exception':'Video URL is Invalid!'}

                                    print('Exception in the current frame:',data1)
                                    except_arr.append(data1)
                                    msg_py['payload'] = except_arr    # this will be displayed in fronted using socket
                                    #node.send(msg_py)   #Node's Output
                                    msg_passing.append(msg_py)
                                    #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)

                                    return msg_py


                        elif (video_ext in ['rtsp','mjpeg']):
                                try:
                                    #print('Reading stream')
                                    return_val,frame = vid_latest_rtsp.read()
                                    print(return_val)
                                    #if we are not getting any frames at the middle , we re assign the video capture
                                    if not return_val:
                                        cnt += 1
                                        print(cnt)
                                        if cnt > 10:
                                            vid_latest_rtsp = RTSVideoCapture(str(video_path))
                                            cnt = 0
                                            print("within cnt > 10") 

                                        continue

                                    if frame is None:
                                        continue
                                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                                    #image = Image.fromarray(frame)
                                    #print('hey')
                                except Exception as e:
                                    #rtsp stream can break due to network issue. so w8 for 1 sec and check return_value is True. Else exit.
                                    print('video delay',e)
                                    # cnt_false = cnt_false + 1

                                    # if cnt_false <60:
                                    #     #print("wait for 1*60 sec")
                                    #     #time.sleep(1)   # Delay for 1 sec (1 seconds).
                                    #     vid_latest_rtsp = RTSVideoCapture(str(video_path))    #Read the latest frame from rtsp stream
                                    #     continue
                                    # else:
                                    #     print('Waited for 1*60 sec to get the stream.No stream. So exiting from inference')
                                    #     break



                        frame_num +=1

                        if (video_ext in ['mp4','webm']):
                            if frame_num ==10:
                                
                                    output_path = '/interplay_v2/public/private/box_counting/'+video_name+'/'+video_name+'_1.webm'
                                    if output_path :
    
                                        # by default VideoCapture returns float instead of int
                                            width = int(vid.get(cv2.CAP_PROP_FRAME_WIDTH))
                                            height = int(vid.get(cv2.CAP_PROP_FRAME_HEIGHT))
                                            fps = int(vid.get(cv2.CAP_PROP_FPS))
                                            codec = cv2.VideoWriter_fourcc(*output_format)
                                            out = cv2.VideoWriter(output_path, codec, fps_p, (width, height))
                                        # out = cv2.VideoWriter(output_path, codec, fps/5, (width, height))
                                            print('fpsss10: ', round(fps_p,0))
                                            fps_p_fix = fps_p
    
    
    
                            
    
                            if frame_num >= 10:
                                mod = fps/round(fps_p_fix,0)
                                mod = round(mod,0)
                                print('mod',mod)
                                if frame_num % mod != 0:
                                    continue
                            #let frame_num 1,2,3 run and settle the fps_p
                            
                            print('Frame #, fps_p: ', frame_num,round(fps_p,0))
                            
                        print('Frame #: ', frame_num)
                        print('Frame Shape #: ', frame.shape)
                        frame_size = frame.shape[:2]
                        image_data = cv2.resize(frame, (input_size, input_size))
                        image_data = image_data / 255.
                        image_data = image_data[np.newaxis, ...].astype(np.float32)
                        start_time = time.time()
                
                        # run detections on tflite if flag is set
                        if framework == 'tflite':
                            interpreter.set_tensor(input_details[0]['index'], image_data)
                            interpreter.invoke()
                            pred = [interpreter.get_tensor(output_details[i]['index']) for i in range(len(output_details))]
                            # run detections using yolov3 if flag is set
                            if model == 'yolov3' and tiny == True:
                                boxes, pred_conf = filter_boxes(pred[1], pred[0], score_threshold=0.25,
                                                                input_shape=tf.constant([input_size, input_size]))
                            else:
                                boxes, pred_conf = filter_boxes(pred[0], pred[1], score_threshold=0.25,
                                                                input_shape=tf.constant([input_size, input_size]))
                        else:
                            batch_data = tf.constant(image_data)
                            pred_bbox = infer(batch_data)
                            for key, value in pred_bbox.items():
                                boxes = value[:, :, 0:4]
                                pred_conf = value[:, :, 4:]
                
                        boxes, scores, classes, valid_detections = tf.image.combined_non_max_suppression(
                            boxes=tf.reshape(boxes, (tf.shape(boxes)[0], -1, 1, 4)),
                            scores=tf.reshape(
                                pred_conf, (tf.shape(pred_conf)[0], -1, tf.shape(pred_conf)[-1])),
                            max_output_size_per_class=50,
                            max_total_size=50,
                            iou_threshold=iou,
                            score_threshold=score
                        )
                
                        # convert data to numpy arrays and slice out unused elements
                        num_objects = valid_detections.numpy()[0]
                        bboxes = boxes.numpy()[0]
                        bboxes = bboxes[0:int(num_objects)]
                        scores = scores.numpy()[0]
                        scores = scores[0:int(num_objects)]
                        classes = classes.numpy()[0]
                        classes = classes[0:int(num_objects)]
                
                        # format bounding boxes from normalized ymin, xmin, ymax, xmax ---> xmin, ymin, width, height
                        original_h, original_w, _ = frame.shape
                        bboxes = utils.format_boxes(bboxes, original_h, original_w)
                
                        # store all predictions in one parameter for simplicity when calling functions
                        pred_bbox = [bboxes, scores, classes, num_objects]
                        print('pred_bbox:',pred_bbox)
                
                        # read in all class names from config
                        class_names = utils.read_class_names(cfg.YOLO.CLASSES)
                        print('class_names_people:',class_names)
                
                        # by default allow all classes in .names file
                        #allowed_classes = list(class_names.values())
                        allowed_classes =['package']
                        # custom allowed classes (uncomment line below to customize tracker for only box)
                        #allowed_classes = ['With_mask','Without_mask','Mask_weared_incorrect','Robber_mask']
                
                        # loop through objects and use class index to get class name, allow only classes in allowed_classes list
                        names = []
                        deleted_indx = []
                        for i in range(num_objects):
                            class_indx = int(classes[i])
                            class_name = class_names[class_indx]
                            if class_name not in allowed_classes:
                                deleted_indx.append(i)
                            else:
                                names.append(class_name)
                        names = np.array(names)
                        count = len(names)
                
                
                        # if count:
                        #     cv2.putText(frame, "Objects being tracked: {}".format(count), (5, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.75, (0, 255, 0), 1)
                        #     print("Objects being tracked: {}".format(count))
                
                
                        # delete detections that are not in allowed_classes
                        bboxes = np.delete(bboxes, deleted_indx, axis=0)
                        scores = np.delete(scores, deleted_indx, axis=0)
                
                        # encode yolo detections and feed to tracker
                        features = encoder(frame, bboxes)
                        detections = [Detection(bbox, score, class_name, feature) for bbox, score, class_name, feature in zip(bboxes, scores, names, features)]
                
                        #initialize color map
                        cmap = plt.get_cmap('tab20b')
                        colors = [cmap(i)[:3] for i in np.linspace(0, 1, 20)]
                
                        # run non-maxima supression
                        boxs = np.array([d.tlwh for d in detections])
                        scores = np.array([d.confidence for d in detections])
                        classes = np.array([d.class_name for d in detections])
                        indices = preprocessing.non_max_suppression(boxs, classes, nms_max_overlap, scores)
                        detections = [detections[i] for i in indices]       
                        
                        print('detections:',detections)
                        print('classes:',classes)
                        print('scores:',scores)

                
                        # Call the tracker
                        tracker.predict()
                        tracker.update(detections)
                
                        # update tracks

                        
                        '''
                        #arunn--
                        for dltrack in tracker.dltracks:
                            print("DL--DL***********************************: ",tracker.trackframes)
                            
                            #Arunn delete tracks
                            try:
                               print(dltrack.track_id)
                               tracker.trackframes.pop(dltrack.track_id)
                            except:
                               print("++++++++++Not available DLLL++++++++++++++++")
                        
                        '''
                        

                        
                        result1 = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                        print("result1 ready")
                     
                        #print total mesage
                        cv2.putText(frame, "Total Box Count: {}".format(countt), (5, 15), cv2.FONT_HERSHEY_COMPLEX_SMALL, 0.75, (0, 255, 0), 1)
                        #print('total box count:',countt)
                        
                        for track in tracker.tracks:
                            if not track.is_confirmed() or track.time_since_update > 1:
                                continue 
                            bbox = track.to_tlbr()
                            class_name = track.get_class()
                            print(track.track_id)
                
                            #Arunn process track details
                            try:

                               

                               
                               dd = tracker.trackframes[int(track.track_id)]
                               dd[1] +=1
                               
                               #if dd[1]>5 and dd[1]%15 !=0:   # Add skipping(which are not sent to face detection) track_id as well. other thing is if box are not coming more than 5 times those are noises. so ignore them
                               #    df_tracking = df_tracking.append({'Frame_id':frame_num,'track_id':track.track_id,'gender_prob':'NF','gender':'NF','age_range':'NF','age_prob':'NF'},ignore_index = True)

                               
                               
                               if dd[1] >2 and dd[2] != "sent":
                                 # wide = int(int(bbox[2])-int(bbox[0]))
                                 # heit = int(int(bbox[3])-int(bbox[1]))
                                 
                                 
                                 
                                 # y2 = bbox[3]
                
                                 # if ((bbox[1]-heit*0.1) < 0):
                                 #   y1 = bbox[1]
                                 # else:
                                 #   y1 = (bbox[1]-heit*0.1)
                                  
                                 # x1 = bbox[0]
                
                                
                                 # x2 = bbox[2]
                                 # new_image = result1[int(y1):int(y1+(y2-y1)/2), 
                                 #    int(x1):int(x2)]
                                 new_image_full = result1[int(bbox[1]):int(bbox[3]), 
                                    int(bbox[0]):int(bbox[2])]
                                   
                                
                                 #------------------------
                                     
                                 # draw bbox on screen
                                 countt=countt+1
                                 #print(countt,"Box : ",bbox)
                                 
                                     
                                 image_path = '/interplay_v2/public/private/box_counting/'+video_name+'/snapshot/'+str(track.track_id)+'_2.jpg'

                                 try:
                                    cv2.imwrite(image_path,new_image_full)
                                    img = Image.fromarray(new_image_full.astype("uint8"))
                                    rawBytes = io.BytesIO()
                                    img.save(rawBytes, "JPEG")
                                    rawBytes.seek(0)
                                    img_base64 = base64.b64encode(rawBytes.getvalue()).decode('ascii')
                                    # print('img_base64',img_base64)
                                    mime = "image/jpeg"
                                    uri = "data:%s;base64,%s"%(mime, img_base64)

                                 except Exception as e:
                                    print(e)
                                    continue
                                
                                 print('Total box Count',countt)

                                 data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':countt,'Track_id':str(track.track_id),'snapshot':image_path,'output_video_path':output,'end_status':False,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':output_frame_path,'img_uri':uri}
                           
                                 # msg['payload'] = data1
                                 # node.send(msg)
                                 msg_py['payload'] = data1    # this will be displayed in fronted using socket
                                 msg_passing.append(msg_py)
                                
                        
                                 dd[2] = "sent"


                                 
                           

                                 tracker.trackframes[int(track.track_id)] = dd
                                 

                               
                               color = colors[int(track.track_id) % len(colors)]
                               color = [i * 255 for i in color]
                                
                               cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])), color, 2)
                               cv2.rectangle(frame, (int(bbox[0]), int(bbox[1]-20)), (int(bbox[0])+(len(class_name)+len(str(track.track_id)))*17, int(bbox[1])), color, -1)
                               # cv2.rectangle(frame, (int(bbox[0]), int(bbox[1]-30)), (int(bbox[0])+(len(class_name)+len(str(track.track_id)))*25, int(bbox[1])), color, -1)
                               # cv2.putText(frame, str(track.track_id)+":"+str(dd[2])+":"+str(dd[3]),(int(bbox[0]), int(bbox[1]-6)),0, 0.5, (255,255,255),1)
                               cv2.putText(frame, str(track.track_id),(int(bbox[0]), int(bbox[1]-6)),0, 0.7, (255,255,255),2)
                               
                               # image_path1 = '/interplay_v2/public/private/box_counting/'+video_name+'/snapshot/'+str(track.track_id)+'_test.jpg'
                               # cv2.imwrite(image_path1,frame)

                
                            except Exception as e:
                               print("++++++++++Not available++++++++++++++++",e)
                               dd = {1:1,2:"NF",3:"NF"}
                
                        
                        
                
                            
                          

                            # if enable info flag then print details about each track
                            if info:
                                print("Tracker ID: {}, Class: {},  BBox Coords (xmin, ymin, xmax, ymax): {}".format(str(track.track_id), class_name, (int(bbox[0]), int(bbox[1]), int(bbox[2]), int(bbox[3]))))
                





                        if (video_ext in ['mp4','webm']):
                            fps_p = 1.0 / (time.time() - start_time)
                            print("FPS02: %.2f" % fps_p)
                            result = np.asarray(frame)
                            # cv2.namedWindow("result", cv2.WINDOW_AUTOSIZE)
                            result = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                            # if not dont_show:
                            #     cv2.imshow("result", result)


                            cv2.imwrite(output_frame_path,result)

                            if frame_num >= 10:
                                if  output_path:
                                    out.write(result)
                                
                        elif (video_ext in ['rtsp','mjpeg']):
                            
                            fps = 1.0 / (time.time() - start_time)
                            print("FPS02: %.2f" % fps)
                            result = np.asarray(frame)
                            # cv2.namedWindow("result", cv2.WINDOW_AUTOSIZE)
                            result = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                            # if not dont_show:
                            #     cv2.imshow("result", result)


                            cv2.imwrite(output_frame_path,result)
                            if should_store_frames == True:
                                if  output_path:
                                    out.write(result)

                #######END INFERENCE
                #For videos inference and save full video. for RTSP streams save last 5 mins frames
                if (video_ext in ['mp4','webm']):
                    data1 = {'video_friendly_name':video_friendly_name,'Input_type':video_ext, 'total_box_count':countt,'Track_id':None,'snapshot':None,'output_video_path':output,'end_status':True,'timestamp':datetime.now().strftime("%d/%m/%Y %H:%M:%S"),'output_live_image':None,'img_uri':None}
    
                    arr_comp = []
                    arr_comp.append(data1)
                    #print("arr_comp",arr_comp)
                    msg_py['payload'] = arr_comp    # this will be displayed in fronted using socket
                    msg_passing.append(msg_py)
                    #requests.post('https://advai.interplay.iterate.ai/nextnode',msg_py)
                    #node.send(msg_py)
                    
                    print(current_process)
                    if len(current_process) > 0:
                        completed_pro  = [process for process in current_process if process == video_name] #identifies the process using the friendly name
                        completed_process.append(completed_pro[0])
                        
                    print('Python function ended. Video inference completed')
                    
                elif (video_ext in ['mjpeg','rtsp']):
                        print('Python function ended. Stream inference completed')
                        #node.warn('Python function ended. Stream inference completed')
                        # global process_request_return
                        # process_request_return = "donepythonfunction"
                ##################
                







            except Exception as e:
                print("Process exception occurred in  video inferencing :",e)
                pass
            
            # InteractiveSession.close()
            session.close()
            return msg_py