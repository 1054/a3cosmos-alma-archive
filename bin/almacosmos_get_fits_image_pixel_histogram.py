#!/usr/bin/env python
# 
# 
# Last updates: 
#      20170224 01:52 CET
#      20170224 13:53 CET <20170224> added a check step to make sure we measure the FitGauss
#      20170228 if FitParam['mu'] < np.min(BinCents[FitRange]) or FitParam['mu'] > np.max(BinCents[FitRange])
#      20250704 fix the issue when a cube has bad channels.
# 



# 
# Check input arguments and pring usage
# 
import os, sys, re
if len(sys.argv) <= 1:
    print("Usage: ")
    print("  almacosmos_get_fits_image_pixel_histogram.py \"InputFitsImage.fits\"")
    print("")
    print("Aim:")
    print("  This code will analyze the pixel histogram distrbution of the input image and make a Gaussian fit to compute the pixel statistics including pixel noise. ")
    print("")
    print("Output:")
    print("  InputFitsImage.pixel.histogram.eps")
    print("  InputFitsImage.pixel.histogram.ylog.eps")
    print("  InputFitsImage.pixel.statistics.txt")
    print("")
    sys.exit()


















import numpy as np
import scipy
import astropy
from astropy.io import fits
import matplotlib
import platform
if sys.version_info < (3, 0):
    if platform.system() == 'Darwin':
        matplotlib.use('Qt5Agg') # must before import pyplot
    elif os.getenv('DISPLAY') != None:
        matplotlib.use('TkAgg') # must before import pyplot
    else:
        matplotlib.use('Agg') # must before import pyplot
import matplotlib.pyplot as pl
import matplotlib.mlab as mlab
from matplotlib.colors import LogNorm
from matplotlib.colors import hex2color, rgb2hex
from matplotlib.ticker import ScalarFormatter, FormatStrFormatter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from almacosmos_get_fits_image_pixel_mode import mode
from almacosmos_fit_Gaussian_1D import fit_Gaussian_1D


#print(pl.rcParams.keys())
#pl.rcParams['font.family'] = 'NGC'
pl.rcParams['font.size'] = 20
pl.rcParams['axes.labelsize'] = 'large'
pl.rcParams['axes.labelpad'] = 12 # padding between axis and xy title (label)
pl.rcParams['xtick.major.pad'] = 10 # padding between ticks and axis
pl.rcParams['ytick.major.pad'] = 10 # padding between ticks and axis
pl.rcParams['xtick.labelsize'] = 18
pl.rcParams['ytick.labelsize'] = 18
pl.rcParams['xtick.minor.visible'] = True # 
pl.rcParams['ytick.minor.visible'] = True # 
pl.rcParams['figure.figsize'] = (21/2.0*0.95), (21/2.0*0.95)/16*9 # width = half A4 width , width/height=16/9. 


fig, axes = pl.subplots() # nrows=2, ncols=2 # ax0, ax1, ax2, ax3 = axes.flatten()


# 
# Get input fits file
# 
FitsFile = sys.argv[1]
print('Input fits file: %s\n'%(FitsFile))

OutFileBase = re.sub(r'\.gz$', r'', FitsFile)


# 
# Read input fits image
# 
FitsStruct = fits.open(FitsFile)
i = 0
FitsImage = None
FitsHeader = None
while True:
    FitsImage = FitsStruct[i].data
    FitsHeader = FitsStruct[i].header
    if FitsImage is not None: 
        if i > 0:
            if 'EXTNAME' in FitsHeader:
                print('Input fits extension: %d "%s"\n'%(i, FitsHeader['EXTNAME']))
            else:
                print('Input fits extension: %d\n'%(i))
        break
    i = i + 1
#print('len(FitsStruct) = %d'%(len(FitsStruct)))


# 
# If it's a cube, check outlier channels [20250704]
# 
if len(FitsImage.shape) >= 3:
    nchan = np.prod(FitsImage.shape[0:-2])
    ny, nx = FitsImage.shape[-2:]
    FitsImage = FitsImage.reshape([nchan, ny, nx])
    SpecArr = np.full(nchan, fill_value=np.nan)
    for i in range(nchan):
        if np.count_nonzero(np.isfinite(FitsImage[i])) >= 3:
            SpecArr[i] = np.nanstd(FitsImage[i])
    #print('SpecArr: {}'.format(SpecArr))
    SpecMed = np.nanmedian(SpecArr)
    SpecStd = np.nanstd(SpecArr-SpecMed)
    BadChanMask = (np.abs(SpecArr-SpecMed)>(3.0*SpecStd))
    GoodChanMask = np.invert(BadChanMask)
    SpecMed = np.nanmedian(SpecArr[GoodChanMask])
    SpecStd = np.nanstd(SpecArr[GoodChanMask]-SpecMed)
    BadChanMask = (np.abs(SpecArr-SpecMed)>(3.0*SpecStd))
    if np.count_nonzero(BadChanMask)>0:
        BadChanList = np.argwhere(BadChanMask).ravel().tolist()
        print('BadChanMask = {}'.format(BadChanList))
        for i in BadChanList:
            FitsImage[i, :, :] = np.nan


# 
# Remove NaN and get the rest Bin pixel values
# 
BinVar = FitsImage.flatten()
BinVar = BinVar[np.logical_and(~np.isnan(BinVar),np.isfinite(BinVar))]
#print('len(BinVar) = %d'%(len(BinVar)))


# 
# Statistics of pixel values
# 
BinMin = np.min(BinVar)
BinMax = np.max(BinVar)
BinMean = np.mean(BinVar)
BinMedian = np.median(BinVar)
BinMode, BinModeCounts = mode(BinVar)
BinSigma = np.std(BinVar)
# output to txt file
with open('%s.pixel.statistics.txt'%(OutFileBase), 'w') as fp:
    print(   "Min    = %.10g"  %(BinMin))
    fp.write("Min    = %.10g\n"%(BinMin))
    print(   "Max    = %.10g"  %(BinMax))
    fp.write("Max    = %.10g\n"%(BinMax))
    print(   "Mean   = %.10g"  %(BinMean))
    fp.write("Mean   = %.10g\n"%(BinMean))
    print(   "Median = %.10g"  %(BinMedian))
    fp.write("Median = %.10g\n"%(BinMedian))
    print(   "Mode   = %.10g"  %(BinMode))
    fp.write("Mode   = %.10g\n"%(BinMode))
    print(   "Sigma  = %.10g"  %(BinSigma))
    fp.write("Sigma  = %.10g\n"%(BinSigma))
    fp.close()


# 
# Inner sigma
# 
FitInnerSigma = 5.0
InnerRange = np.where((BinVar>=(BinMean-FitInnerSigma*BinSigma)) & (BinVar<=(BinMean+FitInnerSigma*BinSigma))) # logical_and (() & ())
InnerMean = np.mean(BinVar[InnerRange])
InnerSigma = np.std(BinVar[InnerRange])
# output to txt file
with open('%s.pixel.statistics.txt'%(OutFileBase), 'a') as fp:
    print(   "Inner_mu    = %.10g   # FitInnerSigma = %.1f"  %(InnerMean, FitInnerSigma))
    fp.write("Inner_mu    = %.10g   # FitInnerSigma = %.1f\n"%(InnerMean, FitInnerSigma))
    print(   "Inner_sigma = %.10g   # FitInnerSigma = %.1f"  %(InnerSigma, FitInnerSigma))
    fp.write("Inner_sigma = %.10g   # FitInnerSigma = %.1f\n"%(InnerSigma, FitInnerSigma))
    fp.close()


# 
# pyplot.show()
# 
#pl.show()


# 
# Loop to make sure we get Gaussian fitting for the histogram
# 

BinNumb = 0
BinStep = int( float(FitsHeader['NAXIS1']) * float(FitsHeader['NAXIS2']) / 1000.0 )
BinLoop = True

if BinStep<1 :
    BinStep = 1

while BinLoop and BinNumb <= (len(BinVar)/17.5):
    # 
    # Bin pixel value histogram
    # 
    if BinNumb<=BinStep*10:
        BinNumb = BinNumb + BinStep
    elif BinNumb<=BinStep*100:
        BinNumb = BinNumb + int(BinStep*1.25)
    elif BinNumb<=BinStep*1000:
        BinNumb = int(BinNumb*1.25)
    else:
        BinNumb = len(BinVar)
        break
    
    
    BinHists, BinEdges, BinPatches = pl.hist(BinVar, BinNumb, histtype='stepfilled', color=hex2color('#0000FF'), linewidth=0.2) # histtype='bar', 'step', 'stepfilled'
    BinCents = (BinEdges[:-1] + BinEdges[1:]) / 2.0
    
    pl.draw()
    #pl.show()
    
    
    # 
    # Fit the histogram
    # 
    #FitInnerSigma = 5.0
    FitRange = []
    FitRange = np.where((BinCents>=(BinMean-FitInnerSigma*BinSigma)) & (BinCents<=(BinMean+FitInnerSigma*BinSigma))) # logical_and (() & ())
    if len(FitRange) == 0:
        FitRange = range(len(BinCents))
    
    print("Fitting_range = %.10g %.10g (nbins = %d, ndata = %d)"%(np.min(BinCents[FitRange]), np.max(BinCents[FitRange]), BinNumb, len(BinVar)))
    # 
    FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
    # 
    # print
    #print(BinCents[FitRange], BinHists[FitRange])
    # 
    # try fitting
    if True:
        try:
            FitGauss, FitParam = fit_Gaussian_1D(BinCents[FitRange], BinHists[FitRange], np.max(BinHists[FitRange]), InnerMean, InnerSigma)
            #print(FitParam)
        except:
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
        # 
        if FitParam['mu'] < np.min(BinCents[FitRange]) or FitParam['mu'] > np.max(BinCents[FitRange]):
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
    # 
    # try fitting
    if FitParam['sigma'] == np.nan or FitParam['sigma'] <= InnerSigma * 0.2:
        try:
            FitGauss, FitParam = fit_Gaussian_1D(BinCents[FitRange], BinHists[FitRange], np.max(BinHists[FitRange]), np.min([BinMode,BinMedian]), BinSigma)
            #print(FitParam)
        except:
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
        # 
        if FitParam['mu'] < np.min(BinCents[FitRange]) or FitParam['mu'] > np.max(BinCents[FitRange]):
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
    # 
    # <20170228> added another trial fitting
    # <20170612> <= 0.0 changed to <= InnerSigma * 0.2
    if FitParam['sigma'] == np.nan or FitParam['sigma'] <= InnerSigma * 0.2:
        try:
            FitGauss, FitParam = fit_Gaussian_1D(BinCents[FitRange], BinHists[FitRange], np.max(BinHists[FitRange]), np.min([BinMode,BinMedian]), BinSigma/2.0)
            #print(FitParam)
        except:
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
        # 
        if FitParam['mu'] < np.min(BinCents[FitRange]) or FitParam['mu'] > np.max(BinCents[FitRange]):
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
    # 
    # <20170228> added another trial fitting
    # <20170612> <= 0.0 changed to <= InnerSigma * 0.2
    if FitParam['sigma'] == np.nan or FitParam['sigma'] <= InnerSigma * 0.2:
        try:
            FitGauss, FitParam = fit_Gaussian_1D(BinCents[FitRange], BinHists[FitRange], np.max(BinHists[FitRange]), np.min([BinMode,BinMedian]), BinSigma*2.0)
            #print(FitParam)
        except:
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
        # 
        if FitParam['mu'] < np.min(BinCents[FitRange]) or FitParam['mu'] > np.max(BinCents[FitRange]):
            FitParam = {'A': np.nan, 'mu': np.nan, 'sigma': np.nan}
    # 
    # <20170224> added a check step to make sure we measure the FitGauss
    # <20170612> <= 0.0 changed to <= InnerSigma * 0.2
    if FitParam['sigma'] != np.nan and FitParam['sigma'] > InnerSigma * 0.2:
        # 
        pl.plot(BinCents[FitRange], FitGauss, color=hex2color('#FF0000'), linewidth=3, linestyle='solid') # marker='o', markerfacecolor='blue', markersize=12)
        #pl.text(FitParam['mu']+1.0*FitParam['sigma'], FitParam['A'], 'sigma = %.10g'%(FitParam['sigma']), color=hex2color('#FF0000'), fontsize=18)
        pl.text(FitParam['mu']+1.0*FitParam['sigma'], FitParam['A'], r'$\sigma$ = %.4f mJy/beam'%(FitParam['sigma']*1e3), color=hex2color('#FF0000'), fontsize=24)
        # output to txt file
        with open('%s.pixel.statistics.txt'%(OutFileBase), 'a') as fp:
            print(   "Gaussian_A     = %.10g"  %(FitParam['A'])     )
            fp.write("Gaussian_A     = %.10g\n"%(FitParam['A'])     )
            print(   "Gaussian_mu    = %.10g"  %(FitParam['mu'])    )
            fp.write("Gaussian_mu    = %.10g\n"%(FitParam['mu'])    )
            print(   "Gaussian_sigma = %.10g"  %(FitParam['sigma']) )
            fp.write("Gaussian_sigma = %.10g\n"%(FitParam['sigma']) )
            fp.close()
        # 
        BinLoop = False # this will jump out of the loop


#FitGauss = mlab.normpdf(BinEdges, BinMean, BinSigma)
#FitGauss = FitGauss / np.max(FitGauss) * np.max(BinHists)
locs,labels = pl.xticks()
pl.xticks(locs, map(lambda x: '%.2f' % x, locs*1e3)) # show x axis in unit of mJy/beam instead of Jy/beam
pl.xlabel("Pixel Value [mJy/beam]")
pl.ylabel("N")


# 
# Save eps
# 
#pl.show()
pl.tight_layout()
print('Saving to %s.pixel.histogram.eps'%(OutFileBase))
fig.savefig('%s.pixel.histogram.eps'%(OutFileBase), format='eps')
#os.system('open "%s.pixel.histogram.eps"'%(OutFileBase))




# 
# Then also plot ylog
# 
#pl.show()
pl.clf()
pl.yscale('log')
pl.hist(BinVar, BinNumb, log=True, histtype='stepfilled', color=hex2color('#0000FF'), linewidth=0.2)
pl.ylim([10**-0.75, (np.max(BinHists))*10**0.35])

if type(FitParam) is dict and len(FitRange)>0:
    if FitParam['sigma'] != np.nan and FitParam['sigma'] > 0.0:
        pl.semilogy(BinCents[FitRange], FitGauss, color=hex2color('#FF0000'), linewidth=3, linestyle='solid') # -- You simply need to use semilogy instead of plot -- http://stackoverflow.com/questions/773814/plot-logarithmic-axes-with-matplotlib-in-python
        #pl.text(FitParam['mu']+1.0*FitParam['sigma'], FitParam['A'], 'sigma = %.10g'%(FitParam['sigma']), color=hex2color('#FF0000'), fontsize=18)
        pl.text(FitParam['mu']+1.0*FitParam['sigma'], FitParam['A'], r'$\sigma$ = %.4f mJy/beam'%(FitParam['sigma']*1e3), color=hex2color('#FF0000'), fontsize=24)

locs,labels = pl.xticks()
pl.xticks(locs, map(lambda x: '%.2f' % x, locs*1e3)) # show x axis in unit of mJy/beam instead of Jy/beam
pl.xlabel("Pixel Value [mJy/beam]")
pl.ylabel("log N")


# 
# Save eps
# 
#pl.show()
pl.tight_layout()
fig.savefig('%s.pixel.histogram.ylog.eps'%(OutFileBase), format='eps')
#os.system('open "%s.pixel.histogram.ylog.eps"'%(OutFileBase))


print('Done!')

