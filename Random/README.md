# prng_test.py
Implements and tests a pseudo-random number gererator.

The "linear congruent generator" algorithm is used where random number X is
generated from the previous X as follows.
    X[n+1] = ( a * X[n] + c ) mod m

