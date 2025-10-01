import json
import re


class Node:
    def __init__(self, shape):  
        self.id = shape['id']
        self.text = shape['text']
        if not shape['comment']:
            self.comment = []
        else:
            self.comment = json.loads(shape['comment'])
        self.type = shape['type']
        self.connections = []
    def hide( self ):
        '''
        Hide the comment if it contains the word "hide"
        '''
        if not self.comment:
            return False
        try:
            for comment_obj in self.comment:
                print( "comment_obj: ", comment_obj )
                for comment in comment_obj.get("Comments", []):
                    if comment.get("Creator") == "Jeremy Villalobos":
                        content = comment.get("Content", "").strip()
                        if content.startswith("hide:"):
                            return True
            return False
        except json.JSONDecodeError:
            print( "Error parsing comment JSON" , self.comment )
            return False
    def jump( self ):
        """
        Get the jump phrase from the comment
        """
        try:
            comments_array = self.comment
            jump = ""
            for comment_obj in comments_array:
                for comment in comment_obj.get("Comments", []):
                    if comment.get("Creator") == "Jeremy Villalobos":
                        content = comment.get("Content", "").strip()
                        if content.startswith("jump:"):
                            jump = content.split("jump:")[1].strip()
                            break
            return jump
            
        except json.JSONDecodeError:
            import traceback
            print(f"Error parsing comment JSON: {traceback.format_exc()}")
            return ""
        
    def process_comment(self):
        """
        Process the comment to remove the first line and the last line
        """
        """
        Process the comment to extract content from Jeremy's comments
        """
        
        if not self.comment:
            return ""
            
        try:
            jeremy_comments = []
            for comment_obj in self.comment:
                for comment in comment_obj.get("Comments", []):
                    if comment.get("Creator") == "Jeremy Villalobos":
                        content = comment.get("Content", "").strip()
                        if content and not content.startswith("jump:"):
                            jeremy_comments.append(content)
            return "\n".join(jeremy_comments)
            
        except json.JSONDecodeError:
            import traceback
            print(f"Error parsing comment JSON: {traceback.format_exc()}")
            return ""


class Connection:
    def __init__(self, source, target, arrow_text):
        self.source = source
        self.target = target
        self.arrow_text = arrow_text
    def __repr__(self):
        return f"Connection(source={self.source}, target={self.target}, arrow_text={self.arrow_text})"

def convert_lucid_diagram_to_md(diagram_json):
    """
    Convert a LucidChart decision tree diagram to markdown format
    """
    output = []
    
    # Parse the diagram JSON
    diagram = diagram_json
    from pprint import pprint
    pprint(  diagram )
    # Dictionary to store node connections
    '''
    Connection is a dictionary of source_id to list of target_ids
    like:
    {
        "1": [
            {
                "target": "2",
                "arrow_text": "Yes"
            },
            {
                "target": "3",
                "arrow_text": "No"
            }
        ],
    }
    '''
    connections = {}
    from pprint import pprint
    # First pass - build connections map
    nodes = {}
    for shape in diagram['shapes']:
        if shape['type'] == 'connector':
            source = shape['source']
            target = shape['target'] 
            if source not in connections:
                connections[source] = []
            connections[source].append(Connection(source, target, shape['arrow_text']))
        else:
            nodes[shape['id']] = Node(shape)
    print(f"connections:")
    pprint(connections)
    # Second pass - generate markdown
    
    for node_id, node in nodes.items():
        if node.type in ['process', 'terminator']:
            process_title = node.text.strip()
            process_content = node.process_comment( )
            
            if node.hide():
                print(f"Hiding {node.id}")
                continue

            print( "Node: ", process_title )
            # Get connected decisions
            decisions = []
            goto = None

            if node.id in connections:
                target_queue = [ (c,1) for c in connections[node.id]]
                while target_queue:
                    connection_info, level = target_queue.pop(0) 
                    target = nodes[connection_info.target]
                    if target.hide():
                        print(f"Hiding {target.id}")
                        continue
                    if target.type == 'decision':
                        '''
                        If the target is a decision, we iterate over the NO path.  And the yes 
                        path is added to the decision list.
                        '''
                        target_connectors = connections[connection_info.target]
                        decision_text = target.text.strip()
                        for decision_connector in target_connectors:
                            arrow_text = decision_connector.arrow_text.strip() if decision_connector else ''
                            if decision_text:
                                if arrow_text == "No":
                                    # Get the target that this "No" path points to
                                    target_target =nodes[decision_connector.target]
                                    if target_target.type == 'decision':
                                        target_queue.append( (decision_connector, level ) )
                                    else:
                                        decisions.append(
                                            "".join([
                                                "\t" * level , 
                                                f"- {add_not(decision_text)}?", 
                                                " goto ",
                                                target_target.text , 
                                                f" section. say: \"{target_target.jump()}\""
                                            ])
                                        )
                                else:
                                    target_target = nodes[decision_connector.target]
                                    decisions.append(
                                        "".join([

                                            "\t" * level , f"- {decision_text}?", " goto ",
                                            target_target.text , f" section. say: \"{target_target.jump()}\""
                                        ])
                                    )
                    if target.type == 'process' and not target.type == 'terminator':
                        '''
                        If the process is targeting a process, then we simply add the jump 
                        to the decision list. 
                        We don't follow connection from the terminator since these are not 
                        executable.
                        '''
                        goto="".join([
                                "- goto ",
                                target.text , f" section. say: {target.jump()}"
                            ])
                        
            
            # Generate markdown section
            if process_title:
                output.append(f"\n## {process_title}")
                if process_content:
                    output.append(f"\n{process_content}")
                    
                if goto:
                    output.append(goto)
                if decisions:
                    output.append("\n- Key questions:")
                    for decision in decisions:
                        if decision:
                            output.append(f"{decision}")
                            
    return '\n'.join(output)

def add_not(decision_text):
    '''
    Add "not" to the decision text if it is not already there.
    If the decision text contains "If", then we add "not" to the "If" part.
    If the decision text does not contain "If", then we add "not" to the beginning of the text.
    '''
    if "If" in decision_text:
        pieces = decision_text.split("If")
        return pieces[0] + "If not " + 'if '.join(pieces[1:])
    else:
        return decision_text

def read_diagram_file(filename):
    """
    Read diagram JSON from file
    """
    """
    Read diagram JSON from file and convert to expected format
    """
    import csv
    import json

    shapes = []
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter=',')
        
        for row in reader:
            shape = {
                'id': row['Id'],
                'text': row['Text Area 1'],
                'comment': row['Comments'] or '',
            }
            
            # Determine shape type based on Shape Library
            if 'Terminator' in row['Name']:
                shape['type'] = 'terminator'
            elif 'Decision' in row['Name']:
                shape['type'] = 'decision'
            elif 'Process' in row['Name']:
                shape['type'] = 'process'
            elif 'Page' in row['Name']:
                continue
            elif 'Line' in row['Name']:
                shape['type'] = 'connector'
                shape['arrow_text'] = row['Text Area 1']
                shape['source'] = row['Line Source']
                shape['target'] = row['Line Destination']
            elif 'Document' in row['Name']:
                continue
            elif 'Text' in row['Name']:
                continue
            else:
                raise ValueError(f"Unknown shape type: {row['Name']}")
            
            shapes.append(shape)
    return {'shapes': shapes}

def write_markdown_file(filename, content):
    """
    Write markdown content to file
    """
    with open(filename, 'w') as f:
        f.write(content)

def convert_diagram(input_file, output_file):
    """
    Convert diagram file to markdown file
    """
    diagram_json = read_diagram_file(input_file)
    #from pprint import pprint
    #pprint(diagram_json)
    markdown = convert_lucid_diagram_to_md(diagram_json)
    write_markdown_file(output_file, markdown)

def main():
    """
    Main function to handle command line arguments and run conversion
    """
    import argparse

    parser = argparse.ArgumentParser(description='Convert Lucidchart diagram to markdown')
    parser.add_argument('input', help='Input diagram file path')
    parser.add_argument('output', help='Output markdown file path')
    
    args = parser.parse_args()
    
    convert_diagram(args.input, args.output)

if __name__ == '__main__':
    main()
