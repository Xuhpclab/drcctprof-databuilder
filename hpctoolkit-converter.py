#!/usr/bin/python3

import os
import sys
sys.path.append('/home/qzhao24/projects/hatchet')
import hatchet as ht
import drcctprof_data_builder as ddb
# import sys
# import json

if __name__ == "__main__":
    dirname = "tests/data/hpctoolkit-cpi-database"

    dirname_full_path = os.path.abspath(dirname)
    builder = ddb.Builder()
    builder.addMetricType(1, "second", "Time")

    gf = ht.GraphFrame.from_hpctoolkit(dirname)
    # print(gf.dataframe.to_dict("records"))
    for row in gf.dataframe.itertuples():
        # print(row)
        node = row[0][0]
        if node.children == []:
            # print(row[2])
            metricMsgList = []
            metricMsgList.append(ddb.MetricMsg(0, row[2], ""))
            contextMsgList = []
            for frame in node.path():
                contextMsgDic = gf.dataframe.loc[(frame, 0)].to_dict()
                # print(context.to_dict())
                file = contextMsgDic['file']
                if file[0] == '.':
                    file = dirname_full_path+file[1:]
                contextMsgList.append(ddb.ContextMsg(contextMsgDic['nid'], file, contextMsgDic['name'], contextMsgDic['name'], 0, contextMsgDic['line']))
            builder.addSample(contextMsgList, metricMsgList)
    builder.generateProfile("test.drcctprof")