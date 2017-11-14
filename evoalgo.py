#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on 03.11.17


@author: L.We
"""
from __future__ import print_function
import array
import random
import collections

from optproblems import Problem, Solved, Cache
from evoalgos.algo import PlusEA
from evoalgos.individual import BinaryIndividual
import form
import time
import deap.algorithms

_tree = lambda: collections.defaultdict(_tree)
nutrients = _tree()
for var in range(350):
    for nut in range(11):
        nutrients[var][nut] = random.randint(0, 1000)



def objective_function(phenome):
    # phenome is the bitstring
    # count ones as an example
    # constraint_eq = abs(nutrient_sum - value)  #
    # constraint_ineq = max(nutrient_sum - ub, 0)  + max(lb - nutrient_sum, 0) # constraint for inequality constraints

    return sum(phenome)


def solution_detector(ea):
    for individual in ea.population:
        if individual.objective_values == 0:
            # exception will be caught by evolutionary algorithm
            raise Solved(individual)
    print(ea.problem.consumed_evaluations, ea.population[0].objective_values)

@form.time_it
def example_one_plus_one():
    dim = 700
    problem = Problem(objective_function, max_evaluations=50000)
    problem = Cache(problem)
    popsize = 1
    num_offspring = 1
    population = []
    for _ in range(popsize):
        ind = BinaryIndividual(num_parents=1)
        ind.genome = [random.randint(0, 1) for _ in range(dim)]
        # for lowest CPU time, array.array is recommended
        ind.genome = array.array("B", ind.genome)
        population.append(ind)

    ea = PlusEA(problem, population, popsize, num_offspring, verbosity=1)
    ea.attach(solution_detector)
    ea.run()
    print(ea.last_termination.found_solution)
    print(problem.consumed_evaluations)


def example_mu_plus_lambda():
    dim = 10000
    problem = Problem(objective_function, max_evaluations=5000)
    problem = Cache(problem)
    popsize = 5
    num_offspring = 10
    population = []
    for _ in range(popsize):
        ind = BinaryIndividual(num_parents=2)
        ind.genome = [random.randint(0, 1) for _ in range(dim)]
        # for lowest CPU time, array.array is recommended
        ind.genome = array.array("B", ind.genome)
        population.append(ind)

    ea = PlusEA(problem, population, popsize, num_offspring, verbosity=1)
    ea.attach(solution_detector)
    ea.run()
    # print(ea.last_termination.found_solution)
    # print(problem.consumed_evaluations)
    for ind in ea.population:
        print(ind.objective_values)


if __name__ == "__main__":
    example_one_plus_one()
    #example_mu_plus_lambda()