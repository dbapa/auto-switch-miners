import configparser
import os, time, subprocess, shlex
import requests, json, urllib
import psutil
import errno, signal

ALGO_SHORTNAMES = {
"ethash":"eth","groestl":"gro","phi1612":"phi","cryptonight":"cn",
"cryptonightv7":"cn7","equihash":"eq","lyra2rev2":"lre","neoscrypt":"ns",
"timetravel10":"tt10","x16r":"x16r","skunkhash":"skh","nist5":"n5","xevan":"xn"}
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#BASE_DIR = os.environ['HOME']
CFG_PATH = os.path.join(BASE_DIR,"input.cfg")
config = configparser.ConfigParser()
config.read(CFG_PATH)
current_algo = ''
current_perf24h = 0.0

# handle to the currently running proc
miner_proc = None
miner_pid = 0

retries = 0

def write_content(section,key,val):
    #config[section][key]= str(val)
    with open(os.path.join(BASE_DIR,"internal.cfg"),'w') as configfile:
        configfile.write(str(val))

def get_content(section, key,d='20'):
    value = d
    try:
        value = config.get(section, key,raw=True)
    except:
        value = d
    return value

def get_section(section):
    ret = None
    try:
        ret = config[section]
    except:
        ret = None
    return ret

def get_uri():
    uri = "https://whattomine.com/coins.json?utf8=%E2%9C%93"

    gpu_cards = get_section("gpus")
    # card names do not get case sensitivized!!
    for gpu in gpu_cards:
        str3 = "&adapt_q_"+gpu+"="+get_content("gpus",gpu)
        uri = uri + str3

    # This block creates the power and hash rate section of params
    algorithms = get_section("algorithms")
    #print("[AutoSwitch] "+type(algorithms))
    for algo in algorithms:
        algo = str(algo).lower()
        if get_content("algorithms",algo) == "1":
            # print("[AutoSwitch] "+"Algo ",algo," is enabled")
            algo_code = ALGO_SHORTNAMES[algo]
            str2 = "&" + algo_code +"=true"
            if algo_code == 'lre':
                algo_code = algo_code + 'v2'
            str1 = "&factor%5B"+algo_code+"_hr%5D="+get_content(algo,"hash-rate","20")+"&factor%5B"+algo_code+"_p%5D="+get_content(algo,"power","90")
            # print("[AutoSwitch] "+str2)
            # print("[AutoSwitch] "+str1)
            uri = str(uri+str2)
            uri = str(uri+str1)

    uri =  uri + "&factor%5Bcost%5D="+get_content("general","power_cost_per_kwh")
    #print("cost:",get_content("params","power_cost_per_kwh"))

    str4 = "&sort=Profitability24&volume=0&revenue=24h&factor%5Bexchanges%5D%5B%5D=&factor%5Bexchanges%5D%5B%5D=binance&factor%5Bexchanges%5D%5B%5D=bitfinex&\
factor%5Bexchanges%5D%5B%5D=bittrex&factor%5Bexchanges%5D%5B%5D=cryptobridge&\
factor%5Bexchanges%5D%5B%5D=cryptopia&factor%5Bexchanges%5D%5B%5D=hitbtc&\
factor%5Bexchanges%5D%5B%5D=poloniex&factor%5Bexchanges%5D%5B%5D=yobit&\
dataset=Main&commit=Calculate"
    uri = uri + str4
    #print("[AutoSwitch] "+"Till now URI:",uri)
    return uri

from collections import OrderedDict

def get_performance(coins_dict):
    unsorted_list = {}
    algo=''
    key=''
    for item in coins_dict:
        if item == 'Nicehash-Equihash' or item == 'Nicehash-Ethash':
            key= item
        else:
            algo=coins_dict[item]['algorithm']
            key = item + '-'+algo
        unsorted_list[key]=format(float(coins_dict[item]['btc_revenue24']),'.8f')
        print("[AutoSwitch] "+"Algorithm:",key," profitability:",unsorted_list[key]) #coins_dict[item]['btc_revenue24'])
    sorted_list = OrderedDict(sorted(unsorted_list.items(),key=lambda t:t[1]))
    #print("[AutoSwitch] "+"Sorted:\n",len(sorted_list))
    # for i in range(len(sorted_list)):
    #     print("[AutoSwitch] "+sorted_list.popitem(last=True)[0])
    return sorted_list


def get_from_whattomine():
    uri = get_uri()
    print("[AutoSwitch] "+"URL:",uri)
    #get_coin_algo_list(data)
    #data = json.load(urllib.request.urlopen(uri))
    r = requests.get(uri)
    data = r.json()
    #print("[AutoSwitch] "+data['coins'])
    performers = get_performance(data['coins'])
    return performers

def change_miner(new_algo,new_perf24h):
    change_trigger = False
    print("[AutoSwitch] "+"been asked to change algo to :",new_algo," with 24hr profitability:",str(new_perf24h))
    global current_algo, current_perf24h, miner_proc
    # check if miner proc has children - which will mean miner is running
    if miner_proc  != None and pid_exists(miner_proc.pid):
        change_trigger = False
    else:
        change_trigger = True
    if current_algo != new_algo or change_trigger:
        # a newer algo is suggested to be fired
        new_miner = get_content("miners",new_algo)
        #miner_file = os.path.join(os.path.dirname(BASE_DIR),new_miner)
        miner_file = os.path.join(BASE_DIR,new_miner)
        if miner_proc != None:
            kill_proc(miner_proc)
        #cmd = "xfce4-terminal --command="+miner_file+" --working-directory="+os.path.dirname(BASE_DIR)
        cmd = miner_file
        #try:
        miner_proc = subprocess.Popen(['bash',cmd]) #,stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #except:
        #    print("[AutoSwitch] "+"Process exited or errored")
        print("[AutoSwitch] "+"Miner switched from:",current_algo,"with 24h:",str(current_perf24h)," to:",new_algo,":",str(new_perf24h)," with proc ID:",miner_proc.pid)
        current_algo = new_algo
        current_perf24h = new_perf24h
        write_content("internal","id",miner_proc.pid) #this PID will be killed at startup
    else:
        #print("[AutoSwitch] "+"Current algo:",current_algo," same as suggested new algo:",new_algo," So no change")
        pass
    return miner_proc

def kill_proc(proc):
    try:
        #print("[AutoSwitch] "+"kill request for:",proc.pid)
        if pid_exists(proc.pid):
            p = psutil.Process(proc.pid)
            p_child = p.children(recursive=True)
            #print("[AutoSwitch] "+"need to kill:",p_child)
            for child in p_child:
                #print("[AutoSwitch] "+"killing children:",child.pid)
                subprocess.call(['kill','-9',str(child.pid)])
            #print("[AutoSwitch] "+"killing main:",proc.pid)
            subprocess.call(['kill','-9',str(proc.pid)])
    except:
        print("[AutoSwitch] "+"exception in kill_proc, likely no proc found for:",proc)
        pass
    return True

def pid_exists(pid):
    """Check whether pid exists in the current process table.
    UNIX only.
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True

def startup():
    ret = False
    try:
        if os.path.isfile(os.path.join(BASE_DIR,"internal.cfg")):
            with open(os.path.join(BASE_DIR,"internal.cfg"),'r') as configfile:
                txt = configfile.readline()
                pid = int(txt)
                print("[AutoSwitch] "+"found process to be killed:",txt," type:",type(txt))
                if pid_exists(pid):
                    p = psutil.Process(pid)
                    if p.isRunning():
                        ret = kill_proc(p)
                #subprocess.call(['kill',txt])
        ret = True
    except:
        print("[AutoSwitch] "+"No evidance of prev. run")
        ret = True
        if os.path.isfile(os.path.join(BASE_DIR,"internal.cfg")):
            os.remove(os.path.join(BASE_DIR,"internal.cfg"))
    return ret

# Will return PASS if no change required, RESTART if new miner proc not Found
# and will return START_DEFAULT if retry attempts exceeded, so start default miner
def check_for_stalled_miner(proc):
    global retries,miner_proc
    ret_flag = "PASS" # indicates no need to change miner
    if proc != None and pid_exists(proc.pid):
        p = psutil.Process(proc.pid)
        proc_children = p.children(recursive=True)
        if len(proc_children) > 0:
            # The miner is running, do nothing and exit
            print("[AutoSwitch] "+" Currently mining:",new_algo)
        else:
            # kill pid and start new miner
            ret = kill_proc(proc)
            if retries > 3:
                # after 3 failed attempts try changing to default miner
                m = "default-miner"
                print("[AutoSwitch] "+"Miner process not detected. Switching to default miner.")
                #miner_proc = change_miner(m,0.00010)
                retries = 0
                ret_flag = "START_DEFAULT"
            else:
                print("[AutoSwitch] "+"Miner process not detected. Attempting to restart miner:",new_algo)
                #miner_proc = change_miner(new_algo,float(new_perf24h))
                retries += 1
                ret_flag = "RESTART"
    else:
        if retries > 3:
            # after 3 failed attempts try changing to default miner
            print("[AutoSwitch] "+"No miner detected. Switching to default miner.")
            m = "default-miner"
            retries = 0
            #miner_proc = change_miner(m,0.00010)
            ret_flag = "START_DEFAULT"
        else:
            print("[AutoSwitch] "+"No miner detected. Attempting to restart miner:",new_algo)
            #miner_proc = change_miner(new_algo,float(new_perf24h))
            retries += 1
            ret_flag = "RESTART"
    return ret_flag


if __name__ == '__main__':
#    global current_algo, miner_proc
current_algo, miner_proc
    #performers = get_from_whattomine()
    if startup() == False:
        print("[AutoSwitch] "+"Another miner instance seems to be running. Please terminate it and try again.")
        exit()
    polling_frequency = get_content("general","polling_frequency")
    preferred_perf_threshold = get_content("general","threshold")
    miners_available = get_section("miners")
    new_algo=''
    new_perf24h = 0.0
    while True:
        performers = get_from_whattomine()

        matchFound = False
        for i in range(len(performers)):
            #print("[AutoSwitch] "+performers.popitem(last=True))
            topper = performers.popitem(last=True)
            print("[AutoSwitch] "+"Most profitable is:",str(topper[0]))
            for miner in miners_available:
                #print("[AutoSwitch] "+"miner:",miner," type:",type(miner)," Tpper:",topper[0])
                if str(topper[0]).lower() == miner:
                    #print("[AutoSwitch] "+"Topper match found")
                    matchFound = True
                elif miner in str(topper[0]).lower():
                    #print("[AutoSwitch] "+"Miner :",miner," part of:",topper)
                    matchFound = True
                if matchFound:
                    new_algo = miner
                    new_perf24h = float(topper[1])
                    break
            #print("[AutoSwitch] "+"exited miner loop..miner found")
            if matchFound:
                break
        #print("[AutoSwitch] "+"Exited Top performers loop..miner found")
                # exit the main for loop as matching miner was found
        if matchFound == True:
            if new_algo == current_algo:
                # There will be no switch, just update the revised perf_rate
                current_perf24h = float(new_perf24h)
                perf_diff = 0
            elif current_perf24h != 0.0:
                perf_x = (new_perf24h - current_perf24h)/current_perf24h
                #print("[AutoSwitch] perf_x:",perf_x," current:",current_perf24h," new:",new_perf24h)
                perf_diff = float(perf_x) - float(preferred_perf_threshold)
                print("[AutoSwitch] "+"Perf difference:",perf_diff)
            else:
                perf_diff = new_perf24h
                #print("[AutoSwitch] "+"Perf difference NOT calculated:",perf_diff)
            # if difference is greater than threshold, need to switch
            if perf_diff > 0:
                miner_proc = change_miner(new_algo,float(new_perf24h))
        # else let mining continue as is
        elif matchFound == False:
            if current_algo == '':
            # that means not running and no match found, so start default miner
                default_miner = miners_available["default-miner"]
                print("[AutoSwitch] "+"No prioritized miner found. Trying default miner:","default-miner")
            # it is not currently mining, so just get top miner and start
                m = "default-miner"
                miner_proc = change_miner(m,0.00010)

        if polling_frequency is None:
            polling_frequency = 600
        step_counter = 60
        i=0
        while True:
            if i==0:
                time.sleep(120)
            else:
                time.sleep(step_counter)
            i += step_counter
            if i > int(polling_frequency):
                break
            else:
                flag = check_for_stalled_miner(miner_proc)
                if flag == "RESTART":
                    miner_proc = change_miner(new_algo,float(new_perf24h))
                elif flag == "START_DEFAULT":
                    miner_proc = change_miner(m,0.00010)

        #time.sleep(int(polling_frequency))
        #print("[AutoSwitch] "+"Will sleep for :", polling_frequency)

#print("[AutoSwitch] "+"Done") # this should never get printed
