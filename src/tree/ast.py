# coding=utf-8
'''
Created on 2015年11月6日

@author: Bert
'''

def get_function_node(neo4j_db, name):
    query = "match (n {type:'Function', name:'%s'}) return n" % name
    records = neo4j_db.cypher.execute(query)    
    return records.one

def get_function_ast_root(neo4j_db, name):
    query = "match (n {type:'Function', name:'%s'})-[:`IS_FUNCTION_OF_AST`]->(m) return m" % name
    records = neo4j_db.cypher.execute(query)
    return records.one

def get_function_file(neo4j_db, name):
    query = "match (n {type:'Function', name:'%s'})<-[:`IS_FILE_OF`]-(m) return m" % name
    records = neo4j_db.cypher.execute(query)
    if records:
        return records.one.properties['filepath']
    else:
        return None

def get_in_node(neo4j_db, node, edge_property=None):
    query = ""
    if edge_property is None:
        query = "start n=node(%d) match (m)-->(n) return m" % node._id
    else:
        query = "start n=node(%d) match (m)-[:`%s`]->(n) return m" % (node._id, edge_property)
    
    records = neo4j_db.cypher.execute(query)
    return records.one

def get_out_nodes(neo4j_db, node, edge_property=None):
    query = ""
    if edge_property is None:
        query = "start n=node(%d) match (n)-->(m) return m order by m.childNum" % node._id
    else:
        query = "start n=node(%d) match (n)-[:`%s`]->(m) return m order by m.childNum" % (node._id, edge_property)
    
    records = neo4j_db.cypher.execute(query)
    
    nodes = []
    for record in records:
        nodes.append(record[0])
    
    return nodes

def get_out_node_property_by_type(neo4j_db, node, type, property_name):
    query = "start n=node(%d) match (n)-[:`IS_AST_PASRENT`]->(m {type:'%s'}) return m.%s" % (node._id, type, property_name)
    records = neo4j_db.cypher.execute(query)
    return records.one
 
def get_function_return_type(neo4j_db, ast_root_node):
    # @func_ast_node 函数ast树的根结点
    query = "start ast_root=node(%d) match(ast_root)-[:`IS_AST_PARENT`]->(m {type:'ReturnType'}) return m.code" % ast_root_node._id
    records = neo4j_db.cypher.execute(query)
    return records.one

def get_function_param_list(neo4j_db, ast_root_node):
    query = '''start ast_root=node(%d) match(ast_root)-[:`IS_AST_PARENT`]->
    (param_list {type:'ParameterList'})-->(param {type:'Paramter'})-->
    (param_type {type:'ParameterType'}) return param_type.code
    ''' % ast_root_node._id
    records = neo4j_db.cypher.execute(query)
    
    if records:
        types = []
        for record in records:
            types.append(record[0])
        return types
    else:
        return [u'void']

def get_all_functions(neo4j_db):
    query = "match (n {type:'Function'}) return n"
    records = neo4j_db.cypher.execute(query)
    
    func_nodes = []
    for record in records:
        func_nodes.append(record[0])
    return func_nodes

class serializedAST:
    
    variable_maps = {'other':'v'}  # 变量与类型映射表
    neo4jdb = None
    data_type_mapping = True
    const_mapping = True
     
    def __init__(self, neo4jdb, data_type_mapping=True, const_mapping=True):
        # @data_type_mapping: True:相同类型变量映射成相同token， False：所有类型变量映射成相同token
        # @const_mapping: True:相同常亮映射到相同token，所有常量映射成相同token
        self.neo4jdb = neo4jdb
        self.data_type_mapping = data_type_mapping
        self.const_mapping = const_mapping
        
    def getParent(self, node):
        return get_in_node(self.neo4jdb, node, edge_property='IS_AST_PARENT')
    
    # 处理Identifier节点
    def parseIndentifierNode(self, node):
        parent = self.getParent(node)
        if parent:
            node_type = parent.properties['type']  # 根据父节点类型进行判断
            
            if "Callee" == node_type:  # 函数类型
                return ["f(0);", 0]  # 默认Identifier没有子节点
            
            elif "Lable" == node_type:  # Lable不进行映射
                return ["Identifier(0);", 0]
            
            elif "GotoStatement" == node_type:  # goto语句的lable也不映射
                return ["Identifier(0);", 0]
            
            else:
                code = node.properties['code']
                var_type = ""
                if self.data_type_mapping:
                    if code in self.variable_maps:
                        var_type = self.variable_maps[code]
                    else:
                        var_type = self.variable_maps['other']
                else:
                    var_type = "v"
                
                return ["%s(0);" % var_type, 0]   
                    
        else:
            print "Error"
            return None
    
    # 处理ParamList节点,建立参数名与参数类型映射表
    def parseParamListNode(self, node):
        nodes = get_out_nodes(self.neo4jdb, node, edge_property='IS_AST_PARENT')
        
        if nodes:
            for n in nodes:
                variable = get_out_node_property_by_type(self.neo4jdb, node, 'Identifier', 'code')
                var_type = get_out_node_property_by_type(self.neo4jdb, node, 'ParamterType', 'code')
                self.variable_maps[variable] = var_type
    
    # 处理变量声明语句：
    def parseIdentifierDeclNode(self, node):
        # 获取变量名和变量类型
        variable = get_out_node_property_by_type(self.neo4jdb, node, 'Identifier', 'code')
        var_type = get_out_node_property_by_type(self.neo4jdb, node, 'IdentifierDeclType', 'code')
        self.variable_maps[variable] = var_type

    # 处理常量
    def parsePrimaryExprNode(self, node):
        const_code = node.properties['code']
        if self.const_mapping:
            return [const_code + "(0);", 0]
        else:
            return ["c(0);", 0]
        
        
    # 类型映射，解决指针与数组、多维数组问题
    def parseType(self, data_type):
        return data_type  # 简单处理
           
    def genSerilizedAST(self, root):
        '''
        @return: a list will be returned, list[0] is the serialized ast string,
                list[1] is the node number of the ast
        @root:  function ast root node
        '''
           
        # AST节点之间以 IS_AST_PARENT 边连接
        res = get_out_nodes(self.neo4jdb, root, edge_property='IS_AST_PARENT')
        
        if res:  # 如果有子节点
            s_ast = ""  # 存储子节点产生的序列化AST字符串
            num = 0  # 当前节点下所引导节点数
            
            # 处理子节点
            for r in res:  # 认为子节点按照childrenNum排序
                
                if(r.properties['type'] == "ReturnType"):
                    continue
                
                if(r.properties['type'] == "ParameterList"):
                    self.parseParamListNode(r)
                    continue
                
                if(r.properties['type'] == "IdentifierDecl"):
                    self.parseIdentifierDeclNode(r)
                    
                ret = self.genSerilizedAST(r)  # 递归调用
                s_ast = s_ast + ret[0]  # 按照子节点的顺序生成AST序列
                num += ret[1]  # 添加子节点所引导的节点数
                num = num + 1  # 将子节点数目也算进去
                                                
            
            # 处理根节点
            t = root.properties['type']
            
            if (t == 'AdditiveExpression' or t == 'AndExpression' or t == 'AssignmentExpr'
                or  t == 'BitAndStatement' or t == 'EqualityExpression' or t == 'ExclusiveOrExpression'
                or t == 'InclusiveOrExpression' or t == 'MultiplicativeExpression' 
                or t == 'OrExpression' or t == 'RelationalExpression' or t == 'ShiftStatement'):
                
                s_ast = root.properties['operator'] + "(%d)" % num + ";" + s_ast
            
            else:    
                s_ast = root.properties['type'] + "(%d)" % num + ";" + s_ast                          
            
            return [s_ast, num]  # 返回值是先AST序列，在节点个数，节点个数对后续操作是没用的
        
        else:  # 处理孤立节点
            num = 0
            t = root.properties['type']
            
            if(t == 'IncDec'):
                s_ast = root.properties['code'] + "(%d)" % num + ";"
                return [s_ast, num]
        
            if (t == 'CastTarget' or t == 'UnaryOperator'):
                s_ast = root.properties['code'] + "(%d)" % num + ";"
                return [s_ast, num]
            
            if (t == 'SizeofOperand'):
                code = root.properties['code']
                var_type = ""
                
                if self.data_type_mapping:
                    if code in self.variable_maps:
                        var_type = self.variable_maps[code]
                    else:
                        var_type = self.variable_maps['other']
                else:
                    var_type = "v"
                s_ast = var_type + "(%d)" % num + ";"
                
                return [s_ast, num]
            
            if(t == 'Identifier'):
                return self.parseIndentifierNode(root)
            
            if(t == 'PrimaryExpression'):
                return self.parsePrimaryExprNode(root)
                               
            else:
                s_ast = root.properties['type'] + "(%d)" % num + ";"
                return [s_ast, num]