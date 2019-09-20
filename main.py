########### Python 3.2 #############
# import http.client, urllib.request, urllib.parse, urllib.error, base64
# import requests
# import json
# from requests.exceptions import BaseHTTPError,Timeout,ConnectionError
import argparse
import os
# from datetime import datetime,timedelta
# import time
# import itertools
import pickle
import plotly
import plotly.graph_objs as go
import numpy as np
# from collections import Counter
# import numpy as np
# from scipy.io import wavfile
# from glob2 import glob

baseUrl ="https://westus.api.cognitive.microsoft.com"
http_proxy = "http://proxy.stc:3128"

proxyDict = {
    "http": http_proxy,
    "https": http_proxy,
}

# key_access = 'ff6b390e932d45c7b7fa5113659ca20e'
# key_access = '4de334fee88749cfaa65210133672316'
key_access = 'c85f126fa8884e6e8e759982c00e5be2'

# etalon_min = timedelta(0,60,0)
def deleteProfile(url,id):

    headers = {
        # Request headers
        'Ocp-Apim-Subscription-Key': key_access
    }

    url = urllib.parse.urljoin(url,"/spid/v1.0/identificationProfiles/{}".format(id))

    r=requests.delete(url=url,headers=headers,proxies=proxyDict)

    if(r.ok):
        print("{} has been deleted".format(id))
    else:
        raise Exception("I can`t delete the profile: {}".format(id))



def getAllProfiles(url):
    headers = {
        # Request headers
        'Ocp-Apim-Subscription-Key': key_access
    }

    url = urllib.parse.urljoin(url,"/spid/v1.0/identificationProfiles?")

    r=requests.get(url=url,headers=headers,proxies=proxyDict)

    if(not r.ok):
        raise Exception("I can`t get profiles`s list")

    return json.loads(r.text)

def createProfile(url):

    headers = {
        # Request headers
        'Content-Type': 'application/json',
        'Ocp-Apim-Subscription-Key': key_access
    }

    locale = {"locale":"en-US"}

    url = urllib.parse.urljoin(url,"/spid/v1.0/identificationProfiles?")

    r=requests.post(url=url,data=json.dumps(locale),headers=headers,proxies=proxyDict)

    if(not r.ok):
        raise Exception(r.status_code)

    return json.loads(r.text)['identificationProfileId']

def createEnrollment(url,id,data):

    headers = {
        # Request headers
        'Content-Type': 'multipart/form-data',
        'Ocp-Apim-Subscription-Key': key_access
    }

    params = urllib.parse.urlencode({
        # Request parameters
        'shortAudio': 'true',
    })

    postfix = "/spid/v1.0/identificationProfiles/{}/enroll?%s".format(id) % params

    url = urllib.parse.urljoin(url,postfix)

    r=requests.post(url=url,data=data,headers=headers,proxies=proxyDict)

    # conn.request("POST", url, data, headers)

    if(r.status_code == 202):
        return r.headers.get("operation-location")
    else:
        raise Exception(r.status_code)



def getOperationStatus(url):


    headers = {
        # Request headers
        'Ocp-Apim-Subscription-Key': key_access
    }

    r = requests.get(url, headers=headers,proxies=proxyDict)

    if(not r.ok):
        response = json.loads(r.text)
        err = "code: " + response["error"]["code"] + " "
        err += response["error"]["message"]
        raise Exception(err)

    return json.loads(r.text)

def speakerIdentification(url,ids,data):

    headers = {
        # Request headers
        'Content-Type': 'multipart/form-data',
        'Ocp-Apim-Subscription-Key': key_access
    }

    params = urllib.parse.urlencode({
        # Request parameters
        'shortAudio': 'true',
    })

    postfix = "/spid/v1.0/identify?identificationProfileIds={}&{}".format(",".join(ids),params)

    url = urllib.parse.urljoin(url,postfix)

    r=requests.post(url=url,data=data,headers=headers,proxies=proxyDict)

    if(r.status_code == 202):
        return r.headers.get("operation-location")
    else:
        raise Exception("Response status: {}".format(r.status_code))


def identificationWavAndModel(path2Wav, path2mvm):

    if (not os.path.exists(path2Wav)):
        raise Exception("File is not exists: {}".format(path2Wav))

    if(not os.path.exists(path2mvm)):
        raise Exception("File is not exists: {}".format(path2Wav))

    with open(path2Wav,"rb") as f:
        with open(path2mvm,"r") as f2:
            id,checkUrl = f2.readline().split("\t");
            checkUrl = str(checkUrl).rstrip("\n")

        status = getOperationStatus(checkUrl)

        procResult = status.get("processingResult")

        if(status.get("status") == "succeeded" and procResult.get("enrollmentStatus") == "Enrolled"):
            return speakerIdentification(baseUrl,[id],f.read())
        else:
            err = 999
            raise Exception(err)


    return None

def processIdentification(infile, outfile, lim = None):

    notEnrollmentCount = 0
    fileResult = outfile

    if(os.path.exists(fileResult)):
        os.remove(fileResult)

    oldtime = datetime.now()
    with open(os.path.join(args.output,infile),"r") as f:

        lines = f.readlines()

        if lim != None:
            lines = lines[0:lim]

        allLines = len(lines)
        count = 0
        errLines = 0
        timeout_counter = 0

        for line in lines:

            print("All lines: {} processed: {} error: {} timeout: {} noenrolled: {}".format(allLines,count,errLines,timeout_counter,notEnrollmentCount))
            now = datetime.now()
            wav_path,model_path = line.split("\t")
            model_path = str(model_path).rstrip("\n")
            try:
                link = identificationWavAndModel(wav_path,model_path)
                count += 1
                with open(fileResult,"a") as out:
                    out.write("{}\t{}\t{}\n".format(wav_path,model_path,link))

            except Exception as e:

                if e.args[0] == 999:
                    notEnrollmentCount += 1
                    print("Error enrollment : {}".format(notEnrollmentCount))
                    continue
                elif e.args[0] == 429:
                    sec = (etalon_min - (now - oldtime) + timedelta(0,30,0))
                    sec = min(sec,etalon_min)
                    sleepTime = min(sec.seconds,60)
                    print("Timeout: {} ".format(sleepTime))
                    time.sleep(sleepTime)
                    oldtime = datetime.now()
                    lines.append(line)
                    timeout_counter += 1
                else:
                    errLines += 1
                    print("Error: {}. {} ".format(errLines,str(e)))
                    continue
    pass


def histogram(data,data2, filename = "tmp_histogram.html"):


    fig = go.Figure()
    trace_data = go.Histogram(histfunc="count", x=data, name="VGSDK", text="SpeechTime" )

    fig.add_trace(trace_data)

    trace_data_2 = go.Histogram(histfunc="count", x=data2, name="Microsoft", text="SpeechTime" )

    fig.add_trace(trace_data_2)

    fig.update_layout(
        title_text='Sampled Results',  # title of plot
        xaxis_title_text='Value',  # xaxis label
        yaxis_title_text='Count',  # yaxis label
        bargap=0.2,  # gap between bars of adjacent location coordinates
        bargroupgap=0.1  # gap between bars of the same location coordinates
    )

    plotly.offline.plot(fig, auto_open=True, filename=filename,include_plotlyjs='cdn',image='jpeg')

    pass
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description="Options");
    parser.add_argument("-i", "--input", help="Input catalog`s wav files",required=True)
    parser.add_argument("-o", "--output", help="Output catalog", default="wav_files",required=True)
    parser.add_argument("-p", "--protocol", help="Protocol", default=None)
    parser.add_argument("-c", "--count", help="Operations count per min", default=20,type=int)
    parser.add_argument("--cmd", help="Commands:[0 - delete all profiles,"
                                      " 1 - enrollment models,"
                                      " 2 - create target protocol,"
                                      " 3 - create imposter protocol,"
                                      " 4 - identification target models,"
                                      " 5 - identification imposter models,"
                                      " 8 - get all profiles]", default=8, type=int)
    args = parser.parse_args()

    #delete all profiles
    if (args.cmd == 0):

        for profile in getAllProfiles(url=baseUrl):
            try:
                id = profile.get('identificationProfileId')
                deleteProfile(url=baseUrl,id=id)
            except Exception as e:
                continue

        exit(0)
    #enroll models
    elif (args.cmd == 1):
        files = glob(os.path.join(args.input,"**","*.wav"),recursive=True)

        count = 0
        allFiles = len(files)
        errFiles = 0

        perMin = 0
        oldtime = datetime.now()

        for file in files:

            now = datetime.now()

            if count % (args.count - 1) == 0 and (now - oldtime) < etalon_min and count != 0:
                sec = (etalon_min - (now - oldtime) + timedelta(0,30,0))
                sec = min(sec,etalon_min)
                print("Timeout: {} ".format(min(sec.seconds,60)))
                time.sleep(min(sec.seconds,60))
                oldtime = datetime.now()
            try:
                t,h = os.path.split(file)
                pathOut = os.path.join(args.output,os.path.split(t)[-1])

                if(not os.path.exists(pathOut)):
                    os.makedirs(pathOut)

                name = os.path.join(pathOut,os.path.splitext(h)[0] + ".mvm")
                id = createProfile(url=baseUrl)

                with open(file,"rb") as data:
                    checkOperationUrl = createEnrollment(url=baseUrl,id=id,data=data.read())
                    with open(name,"w") as f:
                        f.write("{}\t{}\n".format(id,checkOperationUrl))

                count += 1

                print("All files: {} processend: {} error: {}".format(str(allFiles),str(count),str(errFiles)))
            except ConnectionError as e:
                errFiles += 1
                print("Connection error: ".format(e))
            except Timeout as e:
                errFiles += 1
                print("Timeout error: ".format(e))
            except BaseHTTPError as e:
                errFiles += 1
                print("Base HTTP error: ".format(e))
            except Exception as e:
                try:
                    err = int(e.args[0])
                    if err == 429: # too many requests
                        sec = (etalon_min - (now - oldtime) + timedelta(0,30,0))
                        sec = min(sec,etalon_min)
                        print("Timeout: {} ".format(min(sec.seconds,60)))
                        time.sleep(min(sec.seconds,60))
                        oldtime = datetime.now()
                        files.append(file)

                except:
                    errFiles += 1
                    print("Unknown exception: ".format(str(e)))

        with open(os.path.join(args.output,"result.txt"),"w") as out:
            out.write("All files: {} processend: {} error: {}".format(str(allFiles),str(count),str(errFiles)))
    #create target protocol
    elif (args.cmd == 2):
        catalogs = glob(os.path.join(args.output,"*"))

        target_combinations = list()
        for catalog in catalogs:
            files = glob(os.path.join(catalog,"*.mvm"))
            target_combinations.append(list(itertools.combinations(files,2)))

        with open(os.path.join(args.output,"target.txt"),"w") as f:

            for target in target_combinations:
                for item in target:
                    t,h = os.path.split(item[0])
                    _,headPath = os.path.split(args.output)
                    wpath = os.path.normpath(str(t).replace(headPath,""))
                    wfile = os.path.join(wpath,os.path.splitext(h)[0] + ".wav")
                    f.write("{}\t{}\n".format(wfile,item[1]))
    #create imposter protocol
    elif (args.cmd == 3):

        catalogs = glob(os.path.join(args.output,"*"))

        imposter_combinations = list()

        files = list()
        for catalog in catalogs:
            mvms = glob(os.path.join(catalog,"*.mvm"))
            if(len(mvms) > 0):
                files.append( mvms[0])

        imposter_combinations.append(list(itertools.combinations(files,2)))

        with open(os.path.join(args.output,"imposter.txt"),"w") as f:

            for imposter in imposter_combinations:
                for item in imposter:
                    t,h = os.path.split(item[0])
                    _,headPath = os.path.split(args.output)
                    wpath = os.path.normpath(str(t).replace(headPath,""))
                    wfile = os.path.join(wpath,os.path.splitext(h)[0] + ".wav")
                    f.write("{}\t{}\n".format(wfile,item[1]))
    #target identification
    elif (args.cmd == 4):

        notEnrollmentCount = 0
        fileResult = os.path.join(args.output,"identification_result.txt")

        processIdentification("target.txt",fileResult)
    #imposter identification
    elif (args.cmd == 5):

        notEnrollmentCount = 0
        fileResult = os.path.join(args.output,"imposter_identification_result.txt")

        processIdentification("imposter.txt",fileResult,lim=2000)
    #Get status identification
    elif (args.cmd == 6):

        # fileResult = os.path.join(args.output,"identification_result.txt")
        fileResult = os.path.join(args.output,"imposter_identification_result.txt")

        listResult = list()
        with open(fileResult,"r") as f:
            lines = f.readlines()
            allLines = len(lines)
            counter =0
            error = 0

            for line in lines:

                wfile,model,link = str(line).split("\t")
                link = str(link).rstrip("\n")

                try:
                    status = getOperationStatus(link)
                except Exception as e:
                    print("Exception: {}".format(e))
                    exit(0)

                if(status.get("status") == "succeeded"):
                    counter += 1
                else:
                    error += 1

                listResult.append(status.get("processingResult"))

                print("All lines: {} processed: {} error: {}".format(allLines,counter,error))

            with(open(os.path.join(args.output,"imposter_identification_result.pickle"),"wb")) as sf:
                pickle.dump(listResult,sf)

    elif (args.cmd == 7):
        with(open(os.path.join(args.output,"target_identification_result.pickle"),"rb")) as f:
            data = pickle.load(f)
    elif (args.cmd == 8):
        profiles = getAllProfiles(url=baseUrl)
        print("Enrollment profiles: {}".format(len(profiles)))
    elif (args.cmd == 9):

        with open(os.path.join(r"D:\test_data\voxceleb\vgrid\models\result","p.frfa"),"r",encoding="utf-8") as f:

            lines = f.readlines()

            begin = False
            end = False
            frfa = list()

            x = list()
            fr = list()
            fa = list()

            for line in lines:


                if str(line).find("X_FR_FA_POINTS") != -1:
                    if (begin == False):
                        begin = True
                        continue
                    elif begin == True:
                        break

                if( begin == True):
                    try:
                        ix,ifr,ifa = line.rstrip("\n").split(" ")
                        x.append(float(str(ix).rstrip(";")))
                        fr.append(float(str(ifr).rstrip(";")))
                        fa.append(float(str(ifa).rstrip(";")))
                    except:
                        print("being")

            def scatter(x,y,z,filename):

                fig = go.Figure()
                trace_data = go.Scatter(x=x, y=y,mode="lines",name="fr")
                fig.add_trace(trace_data)
                trace_data_2 = go.Scatter(x=x, y=z,mode="lines",name="fa")
                fig.add_trace(trace_data_2)

                fig.update_layout(
                    title_text='Sampled Results',  # title of plot
                    xaxis_title_text='Value',  # xaxis label
                    yaxis_title_text='Count',  # yaxis label
                    bargap=0.2,  # gap between bars of adjacent location coordinates
                    bargroupgap=0.1  # gap between bars of the same location coordinates
                )

                plotly.offline.plot(fig, auto_open=True, filename=filename,include_plotlyjs='cdn',image='jpeg')
                pass
            scatter(x=np.asarray(x), y=np.asarray(fr), z=np.asarray(fa), filename="frfa.html")

        # files = glob(os.path.join(args.output,"**","*.mvm"),recursive=True)
        # out_pickle = os.path.join(args.output,"speech_duration.pickle")
        # out_pickle2 = os.path.join(args.output,"speech_duration_sdk.pickle")
        #
        # speech_duration = list()
        # allFiles = len(files)
        # counter = 0
        # error = 0
        # if not os.path.exists(out_pickle):
        #     for file in files:
        #         try:
        #             with open(file,"r") as f:
        #                 link = f.readline().split("\t")[-1].rstrip("\n")
        #
        #                 status = getOperationStatus(link)
        #                 speech_duration.append(status)
        #                 counter += 1
        #                 print("All files: {} processed: {} error: {}".format(allFiles,counter,error))
        #         except Exception as e:
        #             time.sleep(30)
        #             error += 1
        #             continue
        #
        #     with open(out_pickle,"wb") as f:
        #         pickle.dump(speech_duration,f)
        # else:
        #     with open(out_pickle,"rb") as f:
        #         status = pickle.load(f)
        #
        #         speech_duration = list()
        #         fte = list()
        #         enrolled_wavs = list()
        #
        #         for file in status:
        #
        #             if(file.get("processingResult").get("enrollmentStatus") == "Enrolled"):
        #                 speech_duration.append(file.get("processingResult").get("speechTime"))
        #             else:
        #                 fte.append(file.get("processingResult").get("speechTime"))
        #
        #         histogram(speech_duration,fte)
        #
        #     # with open(out_pickle2,"rb") as f:
        #     #     speech_duration_sdk = pickle.load(f)
        #     #
        #     #     histogram(speech_duration_sdk,speech_duration)

















