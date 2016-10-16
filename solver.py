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

BACKEND_URL = 'https://clerkship-shuffle.appspot.com' #'http://localhost:8080'

def populatebyrow(prob, num_nodes, edge_names, my_obj):
    prob.objective.set_sense(prob.objective.sense.maximize)

    # Make all vars binary
    prob.variables.add(obj=my_obj, names=edge_names)
    for name in edge_names:
        prob.variables.set_types(name, prob.variables.type.binary)

    linear_const = []
    rhs = []
    senses = []
    constraint_names = []

    for i in range(num_nodes):
        node = str(i + 1)
        # Set conservation and capacity constraint for 
        conservation_names = []
        conservation_coeff = []
        capacity_names = []
        capacity_coeff = []
        for edge in edge_names:
            (sending, receiving) = edge.split('_')
            if sending == node:
                conservation_names.append(edge)
                conservation_coeff.append(-1.0)
                capacity_names.append(edge)
                capacity_coeff.append(1.0)
            elif receiving == node:
                conservation_names.append(edge)
                conservation_coeff.append(1.0)
        # Add conservation constraint
        if len(conservation_names) > 0:
            linear_const.append([conservation_names, conservation_coeff])
            rhs.append(0.0)
            senses.append('E')
            constraint_names.append('cons_{}'.format(node))

        # Add capacity constraint
        if len(capacity_names) > 0:
            linear_const.append([capacity_names, capacity_coeff])
            # Since they're binary I can write <= 1 as < 2.0
            # This avoids having to use ranged values
            rhs.append(2.0) 
            senses.append('L')
            constraint_names.append('cap_{}'.format(node))

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

def solve(num_nodes, edge_names, obj):
    try:
        my_prob = cplex.Cplex()
        handle = populatebyrow(my_prob, num_nodes, edge_names, obj)
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
    return results

if __name__ == "__main__":
    data = get_input()
    print data
    results = solve(data['num_nodes'], data['edges'], data['obj'])
    post_matches(results)
