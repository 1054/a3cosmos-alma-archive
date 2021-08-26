#!/usr/bin/env python
# 
# -- from http://stackoverflow.com/questions/11507028/fit-a-gaussian-function
# 


import numpy
from scipy.optimize import curve_fit


# Define model function to be used to fit to the data above:
def Func_Gaussian_1D(x, *p):
    A, mu, sigma = p
    return A*numpy.exp(-(x-mu)**2/(2.*sigma**2))


# Do Gaussian 1D fitting
def fit_Gaussian_1D(x, y, *p): 
    
    # p0 is the initial guess for the fitting coefficients (A, mu and sigma above)
    if p:
        p0 = p
    else:
        p0 = [numpy.max(y), numpy.mean(x), numpy.std(x)]
    
    # Check input, x is BinEdges (or BinCentres), y is BinHistogram
    if len(x) == len(y)+1:
        bin_edges = x
        bin_centres = (bin_edges[:-1] + bin_edges[1:]) / 2.0
    else:
        bin_centres = x
    
    fit_params, fit_matrix = curve_fit(Func_Gaussian_1D, bin_centres, y, p0=p0)
    
    # Get the fitted curve
    fit_curve = Func_Gaussian_1D(bin_centres, *fit_params)
    
    # Fix negative sigma problem
    #fit_params[2] = numpy.sqrt(fit_params[2]**2)
    
    # Return the best-fit curve and parameters
    return fit_curve, {'A':fit_params[0], 'mu':fit_params[1], 'sigma':fit_params[2]}


