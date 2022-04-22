#!/usr/bin/env python3

import sys
sys.path.insert(0, './hatchet')
import hatchet as ht
from pathlib import Path
import drcctprof_data_builder as ddb

root = None
check = True
ID = 0 # manually assign the id number

"""
lists in a list. 
each list in a list presents a path.
each list contains multiple tuples.
a tuple means a node, consists of id, name, file, start line, row, and rows respectively.
Example:
[
    [(name1, id, file, line, start_line, row, rows)], 
    [(name1, id, file, line, start_line, row, rows), (name2, id, file, line, start_line, row, rows)], 
    [(name1, id, file, line, start_line, row, rows), (name3, id, file, line, start_line, row, rows)]
]
"""
all = []


class TreeNode:
    def __init__(self, name, parent, file, line, start_line, row):
        global ID
        self.parent = parent
        self.name = name
        self.children = []
        self.parents = []
        self.id = ID
        ID += 1
        self.file = file
        self.line = line
        self.start_line = start_line
        self.row = row
        self.rows = set()
        self.rows.add(row)
        
        """
        fill the list of self.parents, 
        if two nodes have exact same parents and names of two nodes are same, 
        then consider they are same one.
        """
        p = self.parent
        while p:
            self.parents.append(p.name)
            p = p.parent
    
    def add_child(self, node):
        self.children.append(node)
        return node
        
    def __str__(self, level=0):
        # print all info except row
        
        ret = "\t"*level+repr(self.name)+", id:"+str(self.id)+", line:"+str(self.line)+", startline:"+str(self.start_line)+", rows:"+str(len(self.rows)) +"\n"
        #ret = "\t"*level+repr(self.name)+",rows: "+prt_rows+"\n"
        
        for child in self.children:
            ret += child.__str__(level+1)
        return ret
    
    def __repr__(self):
        return self.name

# check if the node has child(ren)
def has_child(node):
    return node.children is not None


def return_all_paths(node, paths):
    global all
    if node is None:
        return
    paths.append((node.name, node.id, node.file, node.line, node.start_line, node.row, node.rows))
    if has_child(node):
        all.append(list(paths))
    for i in node.children:
        return_all_paths(i, paths)
    paths.pop()


def main(tau_profile_dir, output):
    global root
    global check
    
    builder = ddb.Builder()
    gf = ht.GraphFrame.from_tau(str(tau_profile_dir))
    df = gf.dataframe
    metric_num = 0
    units = []
    """
    Add Metric Type: builder.addMetricType()
    """
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

    nodes = []
    sample_map = {} #key is name, value is the number of samples
    last_row_name, sample_num = None, 0
    rows = gf.dataframe.itertuples()
    for row in rows:
        # print(row)
        node = row[0][0]
        if last_row_name is None:
            sample_num = 1
        elif last_row_name == node:
            sample_num += 1
        else:
            last_row_name = None
            sample_num = 1
        last_row_name = node
        
        path = []
        for cur in node.path():
            path.append(cur)
        
        if node.frame.get('type') != 'function' and node.frame.get('type') != 'statement':
            continue
        rank = row[0][1]
        thread = -1
        if len(row[0]) == 3:
            thread = row[0][2]

        curNode = node
        contextMsgDic = {}
        parent = root
        for idx, val in enumerate(path):
            if idx >= len(path):
                break
            curNode = val
            if thread > -1:
                contextMsgDic = dict(gf.dataframe.loc[(curNode, rank, thread)])
            else:
                contextMsgDic = dict(gf.dataframe.loc[(curNode, rank)])

            file, name, line, startline = contextMsgDic['file'], contextMsgDic['name'], int(contextMsgDic['line']), contextMsgDic['line']
            if str(file) == '0':
                file = "[unknown]"
            if name in sample_map: sample_map[name] = max(sample_num, sample_map[name])
            else:sample_map[name] = sample_num
            # building a tree named root
            if not parent and check: # create one at the beginning
                root = TreeNode(name, None, file, line, startline, row)
                nodes.append(root)
                parent = root
                check = False
            else:
                tree_node = TreeNode(name, parent, file, line, startline, row)
                find_same_node = False
                for i in nodes:
                    #if name == root.name and parent == root.parents and file == root.file and line == root.line:
                    if name == root.name and i.parents == root.parents and i.file == file and i.line == line:
                        if len(path) == 1:
                            i.rows.add(row)
                        find_same_node = True
                        parent = root
                    elif i.name == name and i.parents == tree_node.parents:
                        if i.file == file and i.line == line:
                            cur_name = (str(node).split(','))[0].split(": ")[1]
                            cur_name = cur_name[1:len(cur_name)-1]
                            if cur_name == name:
                                i.rows.add(row)
                            parent = i
                            find_same_node = True
                            break
                if not find_same_node:
                    child = parent.add_child(tree_node)
                    nodes.append(tree_node)
                    parent = child
    
    
    """
    use print(root) to see the whole tree
    """
    #print(root)
    
    paths = []
    return_all_paths(root, paths)
    #print(all)
    for each_path in all:
        sumvalue = 0
        contextMsgList = []
        for each_node in each_path:
            contextMsgList.append(ddb.ContextMsg(each_node[1], each_node[2], each_node[0], each_node[0], each_node[4], each_node[3]))
        # print(each_node[0])
        for r in each_node[6]:
            metricMsgList = []
            for idx in range(metric_num):
                metricValue = 0
                if units[idx]:
                    metricValue = int(r[8 + idx * 2]*1000000)    
                else:
                    metricValue = int(r[8 + idx * 2])
                # print(metricValue)
                metricMsgList.append(ddb.MetricMsg(0, metricValue, ""))
                if metricMsgList[idx].uintValue > 0:
                    sumvalue += 1
            if sumvalue < 1:
                continue        
            builder.addSample(contextMsgList, metricMsgList)
            
    builder.generateProfile(output)
        
DEBUG_MOED = True
def debug():
    main("./tests/data/tau_data", "tau.debug.drcctprof")

if __name__ == "__main__":
    
    if DEBUG_MOED == True:
        debug()
        exit()

    if len(sys.argv[1:]) != 2:
        sys.exit("Invalid Inputs.\nHow to run this file:\npython3 tau-converter.py 'input name' 'output name'")

    input, output = sys.argv[1:]
    if not input or not output:
        sys.exit("Reenter the command again.")

    idx = (output.find('.drcctprof'))
    if '.drcctprof' not in output or len(output[idx:]) != 10:
        sys.exit("Output format should be .drcctprof")

    if not Path(input).is_dir():
        sys.exit("Input path doesn't exist.")
    
    main(input, output)