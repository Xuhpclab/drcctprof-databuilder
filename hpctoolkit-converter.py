#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, './hatchet')
import hatchet as ht
from pathlib import Path
import drcctprof_data_builder as ddb

def main(input_hpctoolkit, output_hpctoolkit):
    
    # Path to HPCToolkit database directory.
    dirname = input_hpctoolkit

    dirname_full_path = os.path.abspath(dirname)
    builder = ddb.Builder()
    
    gf = ht.GraphFrame.from_hpctoolkit(dirname_full_path)
    # reader = HPCToolkitReader(dirname)
    #gf = reader.read()

    # for value in values:
    #     print(value)
    
    df = gf.dataframe
    
    # d = df.to_dict()
    
    metric_num = 0
    units = []

    for column in df.columns.values:
        if "(I)" in column:
            continue
        if "(E)" in column:
            column = column.replace("(E)", "")
            temp = column.rsplit("(", 1)
            des = temp[0].strip()
            unit = ''
            if len(temp) == 2:
                unit = temp[1].split(")")[0].strip()
            units.append(unit == "sec")
            metric_num += 1
            builder.addMetricType(1, unit, des)
            # break
    
    for row in gf.dataframe.itertuples():
        #print(row)
        # the form of index is (node, rank, thread)
        node = row[0][0]
        if node.frame.get('type') != 'function' and node.frame.get('type') != 'statement':
            continue
        rank = row[0][1]
        thread = -1
        if len(row[0]) == 3:
            thread = row[0][2]
            
        # if row[129] == 34962:
        #     print("???")
        
        sumvalue = 0
        metricMsgList = []
        for idx in range(metric_num):
            #sumvalue += row[2 + idx * 2]*1000000
            """
            value = row[2+idx*2]
            if value != 0.0:
                if abs(value) < 0.1:
                    value = value * 100
            """
            #row[2 + idx * 2]*value
            if units[idx]:
                metricMsgList.append(ddb.MetricMsg(0, int(row[2 + idx * 2]*1000000), ""))
            else:
                metricMsgList.append(ddb.MetricMsg(0, int(row[2 + idx * 2]), ""))
            if metricMsgList[idx].uintValue > 0:
                sumvalue += 1
        if sumvalue < 1:
            continue
        # print(row[129], rank, thread, node.frame.get('type'), row[131], row[130], row[133], row[132])
        path = []
        curNode = node
        while True:
            if curNode.frame.get('type') != 'function' and curNode.frame.get('type') != 'statement':
                try:
                    curNode = curNode.parents[0]
                    continue
                except:
                    break
            path.append(curNode)
            try:
                curNode = curNode.parents[0]
            except:
                break
         
        contextMsgList = []
        curNode = node
        parentNode = node
        contextMsgDic = {}
        parentContextMsgDic = {}
        
        for idx, val in enumerate(path):
            if idx >= len(path) - 1:
                break
            curNode = val
            parentNode = path[idx+1]
            if thread > -1:
                contextMsgDic = gf.dataframe.loc[(curNode, rank, thread)].to_dict()
                parentContextMsgDic = gf.dataframe.loc[(parentNode, rank, thread)].to_dict()
            else:
                contextMsgDic = dict(gf.dataframe.loc[(curNode, rank)])
                parentContextMsgDic = dict(gf.dataframe.loc[(parentNode, rank)])
            
            if curNode.frame.get('type') == 'function':
                id, file, name, line, startline = contextMsgDic['nid'], parentContextMsgDic['file'], parentContextMsgDic['name'].split("+:+")[1], int(contextMsgDic['name'].split("+:+")[0]), parentContextMsgDic['line']
            else :
                id, file, name, line, startline = contextMsgDic['nid'], parentContextMsgDic['file'], parentContextMsgDic['name'].split("+:+")[1], contextMsgDic['line'], parentContextMsgDic['line']
            
            # print(id, name, line)


            if file[0] == '.':
                file = dirname_full_path+file[1:]            
            contextMsgList.append(ddb.ContextMsg(id, file, name, name, startline, line))

        # reverse the list because it is bottom-up (children to parents). 
        contextMsgList[:] = contextMsgList[::-1]
        # print(contextMsgList)
        builder.addSample(contextMsgList, metricMsgList)

    builder.generateProfile(output_hpctoolkit)

DEBUG_MOED = False   
def debug():
    main("./tests/data/hpctoolkit-cpi-database", "hpctoolkit.debug.drcctprof")
    
if __name__ == "__main__":

    if DEBUG_MOED == True:
        debug()
        exit()

    # check the number of arguments.
    if len(sys.argv[1:]) != 2:
        sys.exit("Invalid Inputs.\nHow to run this file:\npython3 hpctoolkit-converter.py 'input name' 'output name'")

    input, output = sys.argv[1:]
    if not input or not output:
        sys.exit("Reenter the command again.")

    # check the output format: 
    # if the file contains '.drcctprof' and if the file is end with .drcctprof
    idx = (output.find('.drcctprof'))
    if '.drcctprof' not in output or len(output[idx:]) != 10:
        sys.exit("Output format should be .drcctprof")

    # check the input file
    if not Path(input).is_dir():
        sys.exit("Input path doesn't exist.")

    
    main(input, output)
    
        #print("Unexpected Error")