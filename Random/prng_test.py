#!/usr/bin/python3
"""Implements and tests a pseudo-random number gererator.

The "linear congruent generator" algorithm is used where random number X is
generated from the previous X as follows.

X[n+1] = ( a * X[n] + c ) mod m

For more information, see the google PiDP-11 group discussion at
https://groups.google.com/g/pidp-11/c/OL-FRdJFVa4/m/A-ZzKWLABwAJ """

test_cases = [
        { "a": 9821,  "c": 6925},
        { "a": 25173, "c": 13849},
    ]

# For each test case, try to find random numbers until a repeat occurs.

# Also measure randomness via a D^2 test.  This test is documented in 
# "Problems for Computer Solution" by Fred Gruenberger.  Four random numbers are
# used to select the coordinates of two random points in the unit square:
# ( x1, y1) and ( x2, y2).  The square of distance between the points, d2,
# is given by theorum of pythagoras as ( x2 - x1) ** 2 + ( y2 - y1) ** 2.
# For truly random numbers, half the pairs of points are farther that 0.5 units
# apart or d2 is greater than 0.25.  This test counts how many pairs of points
# have d2 > 0.25.

for test in test_cases:
    a, c = test["a"], test["c"]
    m = test.get( 'm', 2 ** 16)
    seed = test.get( "seed", 0)
    print( "\nStarting with X[0]={seed}, X[n+1] = (X[n] * {a} + {c}) mod {m}"
            .format( **locals()))
    d = {}
    num_gtr = 0
    while seed not in d:
        d[seed] = None
        if len(d) % 4 == 1:
            x1 = float( seed) / m
        if len(d) % 4 == 2:
            y1 = float( seed) / m
        if len(d) % 4 == 3:
            x2 = float( seed) / m
        if len(d) % 4 == 0:
            y2 = float( seed) / m
            d2 = ( x2 - x1) ** 2 + ( y2 - y1) ** 2
            if d2 > 0.25:
                num_gtr += 1
        seed = (seed * a + c) % m      # generate the next random number
    print( "RNG repeated with {}., after finding {} numbers"
            .format( seed, len(d)))
    print( "{:.5}% of d2 is greater than 0.25 (50% expected)".format( 100. * num_gtr / ( len(d) / 4)))


