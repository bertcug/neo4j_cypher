# coding=utf-8
'''
Created on 2015年11月9日

@author: Bert
'''

def get_cfg_nodes(neo4j_db, function_node):
    query = "match (n {functionId:%d, isCFGNode:'True'} return n"
    records = neo4j_db.cypher.execute(query)
   
    nodes = []
    for record in records:
        nodes.append(record[0])
    
    return nodes

def get_cfg_edges(neo4j_db, function_node):
    query = "match (n {functionId:%d, isCFGNode:'True'})-[e:`FLOWS_TO`]->(m) return e"\
             % function_node.properties['functionId']
    records = neo4j_db.cypher.execute(query)
    
    edges = []
    for record in records:
        edges.append(record[0])
    
    return edges


def get_ddg_edges(neo4j_db, function_node):
    query = "match(n {functionId:%d, isCFGNode:'True'})-[e:`REACHES`]->(m) return e"\
             % function_node.properties['functionId']
    records = neo4j_db.cypher.execute(query)
    
    edges = []
    for record in records:
        edges.append(record[0])
    
    return edges

def get_cdg_edges(neo4j_db, function_node):
    query = "match(n {functionId:%d, isCFGNode:'True'})-[e:`CONTROLS`]->(m) return e"\
             % function_node.properties['functionId']
    records = neo4j_db.cypher.execute(query)
    
    edges = []
    for record in records:
        edges.append(record[0])
    
    return edges

def get_func_file(neo4j_db, function_node):
    query = "start n=node(%d) match (m {type:'File'})-[:`IS_FILE_OF`]->(n) return m.filepath" % function_node._id
    records = neo4j_db.cypher.execute(query)
    return records.one
    
    
