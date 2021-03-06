#!/bin/python

import yt.units as units
import yt.utilities.physical_constants as phys_const
from yt import YTArray,YTQuantity
from numpy import pi
import numpy as np
from scipy.integrate import quad
from scipy.interpolate import interp1d
from math import *
import matplotlib.pyplot as plt
import pickle
from cosmological_utils import *
from scipy.interpolate import InterpolatedUnivariateSpline

#cosmology
little_h=.7
omega_lambda=.7
omega_0=.3

#subhalo mass function (Jiang+2014)
fname_SHMF='USMF_M1222_z000.dat'
lMsubH,dn_dlogM_SH=np.loadtxt(fname_SHMF,unpack=True,usecols=(0,1))
interp_SHMF=interp1d(lMsubH,dn_dlogM_SH)

#fname = 'linear_interpolation_SFR_of_zp1_logMh.pkl'
fname = 'logsfr_of_zp1_logMhz0.pkl'
inf = open(fname,'r')
logSF = pickle.load(inf)

#filled SFR (to avoid pbs when interpolating close to max(halo_mass)
sfr_name='logSFR_of_z_logMhalo-filled.pkl'
logSFR_halo=pickle.load(open(sfr_name,'r'))

#get press-shechter data from http://hmf.icrar.org
fname_ps='PS.txt'
Mhost_ST,dn_dlogM_ST=np.loadtxt(fname_ps,unpack=True,skiprows=12,usecols=(0,7))
interp_ST=interp1d(Mhost_ST,dn_dlogM_ST)

fname_gal = 'behroozi_am.pkl'
logSFR_gal=pickle.load(open(fname_gal,'r'))

#maximal mass a halo can have at given z 
fname_maxMass='Mhalo_MaxRedshift.txt'
max_Mhalo,z=np.loadtxt(fname_maxMass,unpack=True,skiprows=1,usecols=(0,1))
interp_max_Mhalo=interp1d(z,max_Mhalo)

#get merger delay times from Drew
# fname_merger='bhbh_mergers_m_150_ecc.dat'
# tdelay,merger_frac_001,merger_frac_01,merger_frac_03=np.loadtxt(fname_merger,unpack=True,skiprows=7)
# interp_merg_01=interp1d(tdelay,merger_frac_01)
# interp_merg_001=interp1d(tdelay,merger_frac_001)
# interp_merg_03=interp1d(tdelay,merger_frac_03)

#get mergers per unit time (Fig.2)
fname_merger_t='bhbh_mergers_dNdt_SGK_m_150_ecc_FIXED.dat'
tdelay,merger_frac_001,merger_frac_01,merger_frac_03=np.loadtxt(fname_merger_t,unpack=True,skiprows=1)
interp_merg_01=interp1d(tdelay,merger_frac_01)
interp_merg_001=interp1d(tdelay,merger_frac_001)
interp_merg_03=interp1d(tdelay,merger_frac_03)


#get sigma(M)
fsigma='our_cosmo_logSig_of_logM_z.pkl'
lsigma_M=pickle.load(open(fsigma,'r'))

#get growth factor (normalized to 1 at z=0)
fgrowth='our_cosmo_logSig_of_logM_zgrowth_factor_of_z.pkl'
growth_z=pickle.load(open(fgrowth,'r'))

    

def EPS_is_awesome(lM0,z,dlM,zobs):

    lprog_min=lM0-4
    lprog_max=lM0-0.0005

    #from Cole+2008, Eqn 5 with f_ps replaced by eq. 7
    dcrit_0=1.686 #Carroll'92)
#    growth=growth_z(zobs)
    growth=growth_z(0.001)/growth_z(zobs)
    dcrit_zobs=dcrit_0/growth
    
#    lprog_min=lM0-3
#    lprog_max=lM0-0.0005

    nmassbins=int(round((lprog_max-lprog_min)/dlM))
    prog_mass=np.linspace(lprog_min,lprog_max,nmassbins)

    sigmas=np.zeros(nmassbins)
    mass_ratio=np.zeros(nmassbins)
    nus=np.zeros(nmassbins)
    nus1=np.zeros(nmassbins)
#    sigma_zobs=10**(lsigma_M(lM0,zobs))
    sigma_zobs=10**(lsigma_M(lM0,0.001))
    for m in range(0,nmassbins):

        mass_ratio[m]=prog_mass[m]-lM0
#        sigmas[m]=10**(lsigma_M(prog_mass[m],z))
        sigmas[m]=10**(lsigma_M(prog_mass[m],0))
#        sigmas[m]=10**(lsigma_M(prog_mass[m],zobs))
        growth=growth_z(z)/growth_z(zobs)
        #growth=growth_z(z)
        dcrit_z=dcrit_0/growth


        #we have absolute values to avoid small negative numbers at very low z
        nus[m]=((dcrit_z-dcrit_zobs)/(sigmas[m]**2-sigma_zobs**2)**(1./2.))

    deriv=np.gradient(np.log10(nus))/np.gradient(prog_mass)
    fit_GF=.4*nus**(3./4.)*np.exp(-nus**(3)/10)
    mass_frac=fit_GF*abs(deriv)

#    print mass_frac,'mass_frac'
#    print fit_GF,'GF'p
#    #mass ratio is log scale, mass frac is linear
    return mass_ratio,mass_frac


def Bond_is_awesome(lM2,z1,dlM2,z2):

    lprog_min=lM2-4
    lprog_max=lM2-0.0005

    #from Cole+2008, Eqn 5 with f_ps replaced by eq. 7
    dcrit_0=1.686 #Carroll'92)
#    growth=growth_z(zobs)
    growth=growth_z(z2)#/growth_z(z2)
    dcrit_z2=dcrit_0/growth
    
#    lprog_min=lM0-3
#    lprog_max=lM0-0.0005

    nmassbins=int(round((lprog_max-lprog_min)/dlM2))
    prog_mass=np.linspace(lprog_min,lprog_max,nmassbins)

    sigmas=np.zeros(nmassbins)
    nus=np.zeros(nmassbins)
    mass_ratio=np.zeros(nmassbins)
    dif=np.zeros(nmassbins)
    interm=np.zeros(nmassbins)
    sigma_z2=10**(lsigma_M(lM2,0))
    s22=sigma_z2**2
    m2=10**lM2
    for m in range(0,nmassbins):

        mass_ratio[m]=prog_mass[m]-lM2
#        sigmas[m]=10**(lsigma_M(prog_mass[m],z))
#        sigmas[m]=10**(lsigma_M(prog_mass[m],0))
        sigmas[m]=10**(lsigma_M(prog_mass[m],0))
        m1=10**prog_mass[m]
#        print m1/1e6,m2/16
        s12=sigmas[m]**2
        growth=growth_z(z1)#/growth_z(z2)
#        growth=growth_z(z)
        dcrit_z1=dcrit_0/growth
        expo=exp(-(dcrit_z1-dcrit_z2)**2/(2*(s12-s22)))
        #interm[m]=(2.*np.arccos(-1.0))**(-1./2)*(dcrit_z1-dcrit_z2)*(s12-s22)**(-3./2.)*expo
        nus[m]=((dcrit_z1-dcrit_z2)/(s12**2-s22**2)**(1./2.))
        interm[m]=(2./np.arccos(-1.0))**(1./2)*nus[m]*exp(-nus[m]**2/2)*m2/m1
#        interm[m]=.4*nus[m]**(3./4.)*np.exp(-nus[m]**(3)/10)#*m2/m1
        dif[m]=s12-s22

#        print mass_ratio[m],dcrit_z1,expo,dif

    deriv=np.gradient(np.log10(nus))/np.gradient(prog_mass)
#    fit_GF=.4*nus**(3./4.)*np.exp(-nus**(3)/10)
    mass_frac=interm*abs(deriv)
#    mass_frac=fit_GF*abs(deriv)
#    print deriv,dif,mass_frac1
    # for m in range(0,nmassbins):
    #     print deriv[m],interm[m],mass_frac[m]
#    print mass_frac,'mass_frac'
    
#    print fit_GF,'GF'p
#    #mass ratio is log scale, mass frac is linear
    return mass_ratio,mass_frac


    
def get_fit(lM0,z):
    dlM=0.001
    
    # for a given redshift and z=0 Halo mass, build the conditional mass function
    #from Cole+2008, Eqn 5 with f_ps replaced by eq. 7
    dcrit_0=1.686 #Carroll'92)
    nmassbins=10
    lprog_min=lM0-3
    lprog_max=lM0-0.0005
#    dlm=(lprog_max-lprog_min)/nmassbins
    nmassbins=int(round((lprog_max-lprog_min)/dlM))
    prog_mass=np.linspace(lprog_min,lprog_max,nmassbins)
    sigmas=np.zeros(nmassbins)
    nus=np.zeros(nmassbins)
    nus1=np.zeros(nmassbins)
    sigma_0=10**(lsigma_M(lM0,z))
    for m in range(0,nmassbins):
        sigmas[m]=10**(lsigma_M(prog_mass[m],z))
        growth=growth_z(z)
        dcrit_z=dcrit_0/growth
        nus[m]=abs((dcrit_z-dcrit_0)/(sigmas[m]**2-sigma_0**2)**(1./2.))

    fit=.4*nus**(3./4.)*np.exp(-nus**(3)/10)
    return nus,fit

 
def derivs(lM0,z):
    dlM=0.001
    
    # for a given redshift and z=0 Halo mass, build the conditional mass function
    #from Cole+2008, Eqn 5 with f_ps replaced by eq. 7
    dcrit_0=1.686 #Carroll'92)
    nmassbins=10
    lprog_min=lM0-3
    lprog_max=lM0-0.0005
#    dlm=(lprog_max-lprog_min)/nmassbins
    nmassbins=int(round((lprog_max-lprog_min)/dlM))
    prog_mass=np.linspace(lprog_min,lprog_max,nmassbins)
    sigmas=np.zeros(nmassbins)
    nus=np.zeros(nmassbins)
    sigma_0=10**(lsigma_M(lM0,z))
    for m in range(0,nmassbins):
        #        print m,prog_mass[m],z
        sigmas[m]=10**(lsigma_M(prog_mass[m],z))
        growth=growth_z(z)
        dcrit_z=dcrit_0/growth
        nus[m]=abs((dcrit_z-dcrit_0)/(sigmas[m]**2-sigma_0**2)**(1./2.))

    deriv=np.gradient(np.log10(nus))/np.gradient(prog_mass)
    #    print len(deriv),len(nus),len(prog_mass)
    return prog_mass,np.log10(nus),deriv


def plot_fits():
    plt.clf()

    for z in (0.5,1,2,4):
        for lMhalo in (12,13.16,15):
            nus,fit=get_fit(lMhalo,z)
            plt.plot(np.log10(nus),np.log10(fit),label='z='+str(z)+' $lM$='+str(lMhalo))
            #    plt.ylim(-7,0)
            #            plt.xlim(-.2,0.9)
    plt.ylim(-2,0)
    plt.xlim(-1,0.7)

    plt.xlabel('log nu')
    plt.ylabel('log Eq.7')
    plt.legend(loc="best")
    
    #    plt.show()
    plt.savefig("lfit_lnu_cole_Fig2.pdf")


def plot_derivs():
    plt.clf()
    #    for z in (0.5,1,2,4):
    z=1
    #    for lMhalo in (12):
    lMhalo=12
    masses,lnu,deriv=derivs(lMhalo,z)
        #        print len(masses),len(lnu),len(deriv)
        #        print deriv
    plt.plot(masses,lnu,label='dlnu/dlM1 z=1,lM=12'+str(lMhalo))
    plt.plot(masses,deriv,label='derivee'+str(lMhalo))
            #            plt.ylim(-2,0.5)
            #plt.xlim(-5,.5)
    plt.ylim(-.5,2)
            #plt.xlim(-1,0.7)
            
    plt.xlabel('log M1')
    plt.ylabel('log nu')
    plt.legend(loc="best")

    #    plt.show()
    plt.savefig("derivs_Cole08.pdf")


def plot_ratios():
    little_h=.7
    lh=np.log10(little_h)
    plt.clf()
    for z in (0.5,1,2,4):
        for lMhalo in (12-little_h,13.15-little_h,15-little_h):
            masses,frac=EPS_is_awesome(lMhalo,z,1e-3,0)
            plt.plot(masses,np.log10(frac),label='z='+str(z)+' $lM$='+str(lMhalo))
            plt.ylim(-2,0.5)
            plt.xlim(-5,.5)
            #    plt.ylim(-2,0)
            #plt.xlim(-1,0.7)

    plt.xlabel('log (M1/M0)')
    plt.ylabel('EPS')
    plt.legend(loc="best")
    
    #    plt.show()
    plt.savefig("EPS_Cole08_Fig1.pdf")


    
def Period_to_Semimajor(P,M1,M2):
    Mtot = M1 + M2
    return (((phys_const.G*Mtot)/(4.*pi*pi)) * P**2)**(1./3.)


def Semimajor_to_Period(A,M1,M2):
    Mtot = M1 + M2
    return np.sqrt((4*np.pi*np.pi) * A**3 / (phys_const.G*Mtot))


def Stellar_mass(lMhalo,zform):
    #get star formation rate
    logSFR_thishost = logSFR(zform+1,lMhalo)
    total_stellar_mass= 10**logSFR_thishost[0]*dt
#    print 'a lMhalo=', lMhalo,' forms', logSFR_thishost[0], 'solar masses in stars at z=',zform
    return log10(total_stellar_mass)

def Coalescence_to_Period(t,M1,M2):
    #Initial period for given coalescence time
    Mtot=M1+M2
    mu=(M1*M2)/(M1+M2)
    a= (phys_const.G**3*Mtot**2*mu*t/phys_const.clight**5*256./5.)**(1./4)
    return Semimajor_to_Period(a,M1,M2)


def metallicity(lMgal):
    #oxygen abundance of Sun in Tremonti+2004
    log_O_sun=(8.69-12) 
    #from Tremonti +2004
    log_O_gal=-1.492+1.847*lMgal-0.08026*lMgal**2-12
    metal=log_O_gal-log_O_sun
    #    print metal,10**metal,log_O_gal+12
    return 10**metal 

def mass_loss(time_since_form):
    #Behroozi+2013,eqn 14, mass lost by a stellar population after certain time
    loss=.05*np.log(1.0+time_since_form/(1.5e6*units.yr))
    return loss

def metallicity_z(lMgal,zform):
#    print 'getting metals',lMgal,zform
    #from Mannucci+2009
    A=-0.0684
    zMan=[.07,0.7,2.2,3.5]
    logM0=[11.18,11.57,12.38,12.8]
    K0=[9.04,9.04,8.99,8.85]
    interp_M0=interp1d(zMan,logM0)
    interp_K0=interp1d(zMan,K0)
    log_O_sun=(8.69-12)     
    if zform<3.5:
        log_O_gal=A*(lMgal-interp_M0(zform))**2+interp_K0(zform)-12#-.7
    else: 
        log_O_gal=A*(lMgal-interp_M0(3.5))**2+interp_K0(3.5)-12#-.7
    metal=log_O_gal-log_O_sun
    return 10**metal 


def metallicity_z_ma(lMgal,zform,calib="PPO4"):
    #compares well with PP04, so we can add for KK04
    #from Ma,Hopkins+2016, 
    #    log_O_sun=(8.69-12)     
    #log_O_gal=+9-12+0.35*(lMgal-10)+0.93*exp(-.43*zform)-1.05
    #metal=log_O_gal-log_O_sun
    
    metal=0.35*(lMgal-10)+0.93*exp(-.43*zform)-1.05+9
    #    print metal,calib,'Z1',zform,lMgal
    if calib=="KK04":
        metal=metal+.35
        #print metal,calib,'Z'
    return metal 


def OH_to_Z(OH):
    #switches from the log10(O/H)+12 definition to the Z/Zsun
    #Ma+2016
    log=OH-9
    return 10**log

def Z_to_OH(Z):
    #switches from Z/Zsun to log10(O/H)+12 definition of metallicity
    return log10(Z)+9
    

def prob(x,mu,sigma):
    #cumulative probability of value below x for normal distribution of mean mu 
    # and standard deviation sigma, variance sigma**2
    return .5*(1+erf((x-mu)/sigma/sqrt(2)))

def prob_log(x,mu,sigma):
    #cumulative probability of value below x for normal distribution of mean mu 
    # and standard deviation sigma, variance sigma**2
    return .5*(1+erf((np.log(x)-mu)/sigma/sqrt(2)))



def Stellar_mass_formed_gal(lMgal,zform,dt):
    logSFR_thishost = logSFR_gal((zform+1),lMgal)
    total_stellar_mass= 10**logSFR_thishost[0]*dt
    return log10(total_stellar_mass)


def SFR_lMhalo(lMhalo,z):
    #first check whether the halo exists in Behroozi data
    #if  low z and low mass halo, ignore it

#    print lMhalo,z,'trying SFR'
    if z>.621:
        max_mass=log10(interp_max_Mhalo(z))
        if lMhalo>max_mass:
            lSFR=-30
        else:
            lSFR = logSFR_halo(z,lMhalo)    
    else:
#        print 'subpart'
        lSFR = logSFR_halo(z,lMhalo)    
#    print lMhalo,'lMhalo SFR',z,10**lSFR
    return 10**lSFR    
    
def Stellar_Mass_Function(lMgal,ldM,zobs):
#,Tomczak+2014


    dM=10**ldM
    if zobs < .5:
        lMstar=10.59
        phi_1=10**(-2.67)
        phi_2=10**(-4.46)
        alpha_1=-1.08
        alpha_2=-2.
    elif zobs <=1.:
        lMstar=10.56
        phi_1=10**(-2.81)
        phi_2=10**(-3.36)
        alpha_1=-0.46
        alpha_2=-1.61

    dif=lMgal-lMstar
    calc=log(10)*exp(-10**dif)*10**dif*(phi_1*10**(dif*alpha_1)+phi_2*10**(dif*alpha_2))

    #    print lMgal,calc*dM

    return calc*dM


def Gal_to_Halo_mass(lMgal,zobs):
    #Behroozi+2010 eq 21.
    a=1+zobs
    am=a-1
    lM1=12.35
    lM0=10.72
    b=0.44
    d=0.57
    g=1.56

    lM1a=0.28
    lM0a=0.55
    ba=0.18
    da=0.17
    ga=2.51

    b=b+ba*am
    d=d+da*am
    g=g+ga*am
    lM1=lM1+lM1a*am
    lM0=lM0+lM0a*am

    ratio=10**(lMgal-lM0)
    lMhalo=lM1+b*(lMgal-lM0)+(ratio**d/(1+ratio**(-g)))-.5
    return lMhalo

def Halo_Mass_Function(lMhalo,ldM):
    dM=10**ldM
    return interp_ST(10**lMhalo)*dM
    
    
def abundance_match_behroozi_2012(Mhalo,z,alpha=None):
    """
    do abundance matching from arxiv 1207.6105v1
    alpha can be specified as the faint end slope
    at z = 0, alpha = -1.412

    as of 10/2014, this jives with what's on his website
    """

    if alpha is not None:
        vara = True
    else:
        vara = False

    from numpy import log10,exp
    def f(x,alpha,delta,gamma):
        top = log10(1+exp(x))**gamma
        bottom = 1 + exp(10**-x) 
        return -log10(10**(alpha*x)+1) + delta*top/bottom

    a = 1./(1.+z)

    nu = exp(-4*a**2)
    log10epsilon = -1.777 + (-0.006*(a-1) - 0.000*z)*nu - 0.119*(a-1)
    epsilon = 10**log10epsilon

    log10M1 = 11.514 + (-1.793*(a-1) - 0.251*z)*nu
    M1 = 10**log10M1

    if alpha is None:
        alpha = -1.412 + (0.731*(a-1))*nu
    else:
        defalpha = -1.412 + (0.731*(a-1))*nu

    delta = 3.508 + (2.608*(a-1) - 0.043*z)*nu
    gamma = 0.316 + (1.319*(a-1) + 0.279*z)*nu

    if not vara:
        log10Mstar = log10(epsilon*M1) + f(log10(Mhalo/M1),alpha,delta,gamma) - f(0,alpha,delta,gamma)

    else:
        from numpy import array,empty_like
        if type(Mhalo) != type(array([1.0,2.0,3.0])):
            if Mhalo >= M1:
                #then I use the default alpha
                log10Mstar = log10(epsilon*M1) + f(log10(Mhalo/M1),defalpha,delta,gamma) - f(0,defalpha,delta,gamma)
            else:
                #then I use my alpha
                log10Mstar = log10(epsilon*M1) + f(log10(Mhalo/M1),alpha,delta,gamma) - f(0,alpha,delta,gamma)
        else:
            log10Mstar = empty_like(Mhalo)
            log10Mstar[Mhalo>=M1] = log10(epsilon*M1) + f(log10(Mhalo[Mhalo>=M1]/M1),defalpha,delta,gamma) - f(0,defalpha,delta,gamma)
            log10Mstar[Mhalo<M1] = log10(epsilon*M1) + f(log10(Mhalo[Mhalo<M1]/M1),alpha,delta,gamma) - f(0,alpha,delta,gamma)

    return 10**log10Mstar



def griddata(x,y,z,imshow=False):
    """
    Takes in three 1D arrays, x, y, and z, all of which must be the same length
    and which together form (xi,yi,zi) tuples, and creates a grid fit to be plotted
    with either imshow or pcolormesh

    if imshow = True, then the return is the array to plot followed by the extent to
    pass.  in this case, the array has been flipped to make it work with imshow; just do:
    H,extent = griddata(x,y,z,imshow=True)
    plt.imshow(H,extent=extent)

    if imshow = False, then the returns are the output of np.meshgrid and
    the gridded Z data; just do:
    X,Y,Z = griddata(x,y,z)
    plt.pcolormesh(X,Y,Z)

    """
    import numpy as np
    assert len(x) == len(y) == len(z)
    assert len(x) >= 2

    x,y,z = np.array(x),np.array(y),np.array(z)
    ux,uy = np.sort(np.unique(x)),np.sort(np.unique(y))
    X,Y = np.meshgrid(ux,uy)
    result = np.empty_like(X)
    for ii in range(ux.shape[0]):
        for jj in range(uy.shape[0]):
            tx,ty = X[jj,ii],Y[jj,ii]
            loc = (x==tx)&(y==ty)
            assert loc[loc].shape[0] == 1
            result[jj,ii] = z[loc]

    if imshow:
        extent = [ux[0]-(ux[1]-ux[0])/2.,ux[-1]+(ux[-1]-ux[-2])/2.,uy[0]-(uy[1]-uy[0])/2.,uy[-1]+(uy[-1]-uy[-2])/2.]
        return result[::-1],extent
    else:
        #now I need to offset the ux and uy arrays, which indicate the centers of the squares, by 1/2 so that they instead indicate the corners
        #need to make them go one above and one below
        nux = np.append(ux[0]-(ux[1]-ux[0]),ux) #make it go one further below
        nux = np.append(nux,nux[-1]+(nux[-1]-nux[-2]))

        nuy = np.append(uy[0]-(uy[1]-uy[0]),uy)
        nuy = np.append(nuy,nuy[-1]+(nuy[-1]-nuy[-2]))

        ox = (nux[:-1]+nux[1:])/2.
        oy = (nuy[:-1]+nuy[1:])/2.

        X,Y = np.meshgrid(ox,oy)

        return X,Y,result
