from __future__ import print_function
from __future__ import division
import sys
import shlex
import cmd
import re
import math

class Iteration(cmd.Cmd):
    prompt = ''

    def __init__(self):
        cmd.Cmd.__init__(self, completekey=None)
        self.graph = Graph()

    def parseline(self, line):
        line = line.strip()
        if not line:
            return None, None, line
        elif line[0] == '?':
            line = 'help ' + line[1:]
        elif line[0] == '!':
            if hasattr(self, 'do_shell'):
                line = 'shell ' + line[1:]
            else:
                return None, None, line
        i, n = 0, len(line)
        while i < n and line[i] != ' ':
            i+=1
        cmd, arg = line[:i], line[i:].strip()
        return cmd, arg, line

    def do_a(self, args):
        pargs = (ParseLine(args, 'do_a'))
        if pargs:
            self.graph.AddStreet(*pargs)

    def do_r(self, args):
        pargs = (ParseLine(args, 'do_r'))
        if pargs:
            self.graph.RemoveStreet(*pargs)

    def do_c(self, args):
        pargs = (ParseLine(args, 'do_c'))
        if pargs:
            self.graph.ChangeStreet(*pargs)

    def do_g(self, args):
        if not args:
            self.graph.GenerateGraph()
            print(self.graph)
        else:
            print('Error: Invalid arguments', file=sys.stderr)

    def do_exit(self,args):
        return True

    def postcmd(self, stop, line):
        if(not line or line=='EOF'):
            stop = True
        return stop

    def default(self, line):
        if line != 'EOF':
            print('Error: The command you entered was not found "{0}"'.format(line), file=sys.stderr)

    def emptyline(self):
        pass


class Graph(object):
    def __init__(self):
        self.past_list = {}
        self.vertex_list = {}
        self.edge_list = set([])
        self.intersection_list = set([])

    def __str__(self):
        str = 'V = {\n'
        for v, v_id in sorted(self.vertex_list.items(), key=lambda x: x[1]):
            if type(v[0]) == 'float' or type(v[1]) == 'float':
                # xcrd, ycrd = int(round(v[0], 2)), int(round(v[1], 2))
                xcrd, ycrd = round(v[0], 2), round(v[1], 2)

            else:
                xcrd, ycrd = v[0], v[1]
            str += '  {0}: ({1},{2})\n'.format( v_id, xcrd, ycrd)
        str += '}\nE = {\n'
        for edge in self.edge_list:
            temp = list(edge)
            str += '  <{0},{1}>,\n'.format(temp[0],temp[1])
        str = str[:-2] + '\n}'

        return str

    def AddStreet(self, strt, vertex_list):
        if vertex_list:
            if strt in self.past_list:
                print('Error: You already have \"{0}\" in the graph'.format(strt), file=sys.stderr)
            else:
                self.past_list[strt] = vertex_list
                return True
        else:
            print('Error: a command has no vertices specified', file=sys.stderr)

        return False

    def ChangeStreet(self, strt, vertex_list):
        if vertex_list:
            if strt in self.past_list:
                self.past_list[strt] = vertex_list
                return True
            else:
                print('Error: c specified for a street \"{0}\" that does not exist'.format(strt), file=sys.stderr)
        else:
            print('Error: c command has no vertices specified', file=sys.stderr)

        return False

    def RemoveStreet(self, strt, *args):
        if strt in self.past_list:
            del self.past_list[strt]
            return True
        else:
            print('Error: r specified for a street \"{0}\" that does not exist'.format(strt), file=sys.stderr)

        return False

    def GenerateGraph(self):

        self.edge_list = set([])
        temp_graph = {}
        temp_intersections = set([])

        for strt, points in self.past_list.iteritems():
            temp_graph[strt] = []

            # loop through edges of street
            for i in xrange(len(points)-1):
                temp_p_to_add = [] # need this list because can have more than one intersection per segement

                # Loop through all other streets to find intersections
                for strt2, points_2 in self.past_list.iteritems():
                    if strt != strt2:
                        # loop through other streets segments
                        for j in xrange(len(points_2)-1):
                            inter_p = intersect(points[i], points[i+1], points_2[j], points_2[j+1])
                            if inter_p:
                                [temp_intersections.add(x) for x in inter_p]
                                [temp_p_to_add.append(x) for x in inter_p if (x != points[i] and x != points[i+1])]

                # add first point of segement if valid
                if (points[i] in temp_intersections # first point is an intersection
                        or points[i+1] in temp_intersections #next point is an intersection
                        or len(temp_p_to_add) > 0 # there exists an intersection with the segment
                        or (temp_graph[strt] or [None])[-1] in temp_intersections): # previous point is an intersection
                    temp_graph[strt].append(points[i])

                # insert all intersections by order of distance to segment if more than one
                if len(temp_p_to_add) > 1:
                    temp_p_to_add = list(set(temp_p_to_add)) # remove duplicates
                    temp_dist = [distance(p, points[i]) for p in temp_p_to_add]
                    temp_dist, temp_p_to_add = zip(*sorted(zip(temp_dist, temp_p_to_add))) # sort the list by distance
                for temp_p in temp_p_to_add:
                    temp_graph[strt].append(temp_p)

            # add last point if valid
            if (temp_graph[strt] or [None])[-1] in temp_intersections:
                temp_graph[strt].append(points[-1])

        # remove all points from graph that are not in new graph
        to_remove = set([])
        for _, v in temp_graph.iteritems():
            [to_remove.add(x) for x in v]
        to_remove = set(self.vertex_list.keys()) - temp_intersections
        {self.vertex_list.pop(x) for x in to_remove}
        self.intersection_list = temp_intersections

        # add remaining points that dont yet have an id
        i = 1
        for strt, vertex_list in temp_graph.iteritems():
            prev = None
            for index, vertex in enumerate(vertex_list):
                # if vertex doesnt exist, add it
                if vertex not in self.vertex_list:
                    #find an id that isn't used
                    while i in self.vertex_list.values():
                        i += 1
                    self.vertex_list[vertex] = i

                # create edge if valid
                v_id = self.vertex_list[vertex]
                if(index > 0 and (vertex in self.intersection_list or prev in self.intersection_list) ):
                    self.edge_list.add(frozenset([v_id, self.vertex_list.get(prev)]))
                prev = vertex

        return

def ParseLine(args, func):
    """return a list [street, [list of points]]
        returns False if Error
    """
    if not args:
        print('Error: invalid input', file=sys.stderr)
        return False
    try:
        temp = shlex.split(args)
    except:
        print('Error: Invalid input', file=sys.stderr)
        return False

    strt = temp[0].lower()
    if re.search(r'[^A-Za-z0-9 ]', strt):
        print('Error: Invalid character in street name', file=sys.stderr)
        return False

    if len(temp) > 1:
        if func == 'do_r':
            print('Error: r command has too many arguments', file=sys.stderr)
            return False
        vertex_list = ''.join(temp[1:])
        if re.search(r'[^0-9,\(\)\- ]', vertex_list):
            print('Error: Invalid character in vertices', file=sys.stderr)
            return False

        # Check all vertices have open and closing parentheses
        opening_paren_num = vertex_list.count('(')
        closing_paren_num = vertex_list.count(')')
        if opening_paren_num != closing_paren_num:
            print('Error: Parenthesis misssing', file=sys.stderr)
            return False

        # match everything between '(' and ')'
        regex = r'\((.*?)\)+?'
        vertex_list = re.findall(regex, vertex_list)
        parsed_vertexlist = []

        # Cast all inputs to tuples of type int
        try:
            for vertex in vertex_list:
                coords = vertex.split(',')
                if len(coords) != 2:
                    raise Exception
                parsed_vertexlist.append(tuple([int(x) for x in coords]))
        except:
            print('Error: Vertices format did not match. Should be separated by ,', file=sys.stderr)
            return False

        if (len(parsed_vertexlist) == 0 or
            len(parsed_vertexlist) != opening_paren_num):

            print('Error: Invalid vertices', file=sys.stderr)
            return False

        return [strt, parsed_vertexlist]

    else:
        return [strt, None]

    return False

def distance(p1, p2):
    p1x, p1y = p1
    p2x, p2y = p2

    dist = math.sqrt((p1x-p2x)**2 + (p1y-p2y)**2)
    return dist

def intersect(p1, p2, p3, p4):

    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]
    x3, y3 = p3[0], p3[1]
    x4, y4 = p4[0], p4[1]

    sgmt1_xmin = min(x1,x2)
    sgmt1_xmax = max(x1,x2)
    sgmt2_xmin = min(x3,x4)
    sgmt2_xmax = max(x3,x4)
    sgmt1_ymin = min(y1,y2)
    sgmt1_ymax = max(y1,y2)
    sgmt2_ymin = min(y3,y4)
    sgmt2_ymax = max(y3,y4)
    x_interval = (max(sgmt1_xmin, sgmt2_xmin), min(sgmt1_xmax, sgmt2_xmax))
    y_interval = (max(sgmt1_ymin, sgmt2_ymin), min(sgmt1_ymax, sgmt2_ymax))

    # check for vertical overlapping lines
    if x1 == x2 == x3 == x4:
        pnts = [p1,p2,p3,p4]
        intersection_list = []
        for pnt in pnts:
            if y_interval[0] <= pnt[1] <= y_interval[1]:
                intersection_list.append(pnt)
        return intersection_list

    # check equations of lines
    elif x1 != x2 and x3 != x4:
        m1 = (y2-y1)/(x2-x1)
        b1 = y1-m1*x1
        m2 = (y4-y3)/(x4-x3)
        b2 = y3-m2*x3
        # check if line equations are equal
        if m1 == m2 and b1 == b2:
            pnts = [p1,p2,p3,p4]
            intersection_list = []
            for pnt in pnts:
                if (x_interval[0] <= pnt[0] <= x_interval[1] and y_interval[0] <= pnt[1] <= y_interval[1]):
                    intersection_list.append(pnt)
            return intersection_list

    xnum = ((x1*y2-y1*x2)*(x3-x4) - (x1-x2)*(x3*y4-y3*x4))
    xden = ((x1-x2)*(y3-y4) - (y1-y2)*(x3-x4))

    ynum = (x1*y2 - y1*x2)*(y3-y4) - (y1-y2)*(x3*y4-y3*x4)
    yden = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
    try:
        xcrd =  xnum / xden
        ycrd = ynum / yden
    except ZeroDivisionError:
        return []

    if (xcrd < x_interval[0] or xcrd > x_interval[1] or ycrd < y_interval[0] or ycrd > y_interval[1]):
        return []

    return [(round(xcrd,2), round(ycrd,2))]

def main(args):
    prgobj = Iteration()
    prgobj.cmdloop()

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
