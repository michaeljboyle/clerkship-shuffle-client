#!/usr/bin/python
# ---------------------------------------------------------------------------
# File: lpex1.py
# Version 12.6.3
# ---------------------------------------------------------------------------
# Licensed Materials - Property of IBM
# 5725-A06 5725-A29 5724-Y48 5724-Y49 5724-Y54 5724-Y55 5655-Y21
# Copyright IBM Corporation 2009, 2015. All Rights Reserved.
#
# US Government Users Restricted Rights - Use, duplication or
# disclosure restricted by GSA ADP Schedule Contract with
# IBM Corp.
# ---------------------------------------------------------------------------
#
# lpex1.py - Entering and optimizing a problem.  Demonstrates different
#            methods for creating a problem.
#
# The user has to choose the method on the command line:
#
#    python lpex1.py  -r     generates the problem by adding rows
#    python lpex1.py  -c     generates the problem by adding columns
#    python lpex1.py  -n     generates the problem by adding a list of
#                            coefficients

import sys
import requests
import json

import cplex
from cplex.exceptions import CplexError


"""
Maximize
s12 + s21 + s23 + s31
subject to
s31 + s21 - s12 = 0
s12 - s21 - s23 = 0
s23 - s31 = 0
s12 <= 1
s23 + s21 <= 1
s31 <= 1
with these bounds
    all vars binary
"""

BACKEND_URL = 'https://clerkship-shuffle.appspot.com' #'http://localhost:8080' #

def populatebyrow(prob, nodes, edge_names, my_obj, connected_trades):
    prob.objective.set_sense(prob.objective.sense.maximize)

    # Make all vars binary
    prob.variables.add(obj=my_obj, names=edge_names, types=[prob.variables.type.binary] * len(my_obj))

    linear_const = []
    rhs = []
    senses = []
    constraint_names = []

    for node in nodes:
        print 'node %s' % node
        # Set conservation and capacity constraint for 
        conservation_names = []
        conservation_coeff = []
        capacity_names = []
        capacity_coeff = []
        for i, edge in enumerate(edge_names):
            print '%s edge %s' % (i, edge)
            (sending, receiving) = edge.split('_')
            if sending == node:
                print 'sending node is this node'
                conservation_names.append(i)
                conservation_coeff.append(-1.0)
                capacity_names.append(i)
                capacity_coeff.append(1.0)
                print conservation_names
                print conservation_coeff
                print capacity_names
                print capacity_coeff
            elif receiving == node:
                print 'receiving node is this node'
                conservation_names.append(i)
                conservation_coeff.append(1.0)
                print conservation_names
                print conservation_coeff
        # Add conservation constraint
        if len(conservation_names) > 0:
            print 'conservation'
            print conservation_names
            print conservation_coeff
            linear_const.append(cplex.SparsePair(ind = conservation_names, val = conservation_coeff))
            rhs.append(0.0)
            senses.append('E')
            constraint_names.append('cons_{}'.format(node))
        else:
            print 'no conservation'

        # Add capacity constraint
        if len(capacity_names) > 0:
            print 'capacity'
            print capacity_names
            print capacity_coeff
            linear_const.append(cplex.SparsePair(ind = capacity_names, val = capacity_coeff))
            # Since they're binary I can write <= 1 as < 2.0
            # This avoids having to use ranged values
            rhs.append(2.0) 
            senses.append('L')
            constraint_names.append('cap_{}'.format(node))
        else:
            print 'no capacity'

    for node_group in connected_trades:
        # Coeff sequence is 1, 1, 2, 4
        coeff_map = {0: 1, 1: 1, 2: 2, 3: 4}
        indices = []
        coeffs = []
        for i, node in enumerate(node_group):
            coeff = coeff_map[i]
            if i == (len(node_group) - 1):
                # make the greatest coeff negative
                coeff = -coeff
            # match edges and their indices to the node
            for index, edge in enumerate(edge_names):
                donor_node = edge.split('_')[0]
                if donor_node == node:
                    indices.append(index)
                    coeffs.append(coeff)
        if coeffs:
            linear_const.append(cplex.SparsePair(ind = indices, val = coeffs))
            rhs.append(0)
            senses.append('E')
            constraint_names.append('connectedtrade_{}'.format(node))


    print 'adding linear constraints to problem'

    prob.linear_constraints.add(lin_expr=linear_const, senses=senses,
                                rhs=rhs, names=constraint_names)

    # because there are two arguments, they are taken to specify a range
    # thus, cols is the entire constraint matrix as a list of column vectors
    #cols = prob.variables.get_cols(0, num_nodes - 1)

def get_input():
    url = BACKEND_URL + '/cplex'
    response = requests.get(url)
    response_json = response.json()
    return response_json['data']

def post_matches(results):
    url = BACKEND_URL + '/match'
    response = requests.post(url, json={'data': results})
    print response.text

def solve(nodes, edge_names, obj, connected_trades):
    try:
        my_prob = cplex.Cplex()
        handle = populatebyrow(my_prob, nodes, edge_names, obj, connected_trades)
        my_prob.solve()
    except CplexError as exc:
        print exc
        return

    numrows = my_prob.linear_constraints.get_num()
    numcols = my_prob.variables.get_num()

    x = my_prob.solution.get_values()
    results = {}
    matches = 0
    for j in range(numcols):
        if x[j] == 1.0:
            matches += 1
            sending, receiving = edge_names[j].split('_')
            if sending not in results:
                results[sending] = {}
            if receiving not in results:
                results[receiving] = {}
            results[sending]['match_to_current'] = receiving
            results[receiving]['match_to_desired'] = sending
        print("Column {}:  Value = {}".format(
              edge_names[j], x[j]))
    print '{} matches found'.format(matches)
    print results
    return results

if __name__ == "__main__":
    data = get_input()
    print data
    results = solve(data['nodes'], data['edges'], data['obj'], data['connected_trades'])
    post_matches(results)
