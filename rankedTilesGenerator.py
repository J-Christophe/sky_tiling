'''
Authors: Shaon Ghosh, Shasvath Kapadia, Deep Chatterjee
Email: ghosh4@uwm.edu
'''


import numpy as np
import pylab as pl
import pickle
import sys
from math import ceil
import healpy as hp
from scipy import interpolate

import time
import datetime

from astropy.time import Time
from astropy import units as u
from astropy.coordinates import get_sun
from astropy.coordinates import SkyCoord, EarthLocation, AltAz

# from AllSkyMap_basic import AllSkyMap



class RankedTileGenerator:
	def __init__(self, skymapfile):
		self.skymap = hp.read_map(skymapfile, verbose=False)
		npix = len(self.skymap)
		self.nside = hp.npix2nside(npix)
		self.preCompDictFiles = {64:'preComputed_pixel_indices_64.dat', 
							128:'preComputed_pixel_indices_128.dat', 
							256:'preComputed_pixel_indices_256.dat',
							512:'preComputed_pixel_indices_512.dat',
							1024:'preComputed_pixel_indices_1024.dat',
							2048:'preComputed_pixel_indices_2048.dat'}
				

	def sourceTile(self, ra, dec, tiles):
		'''
		METHOD     :: This method takes the position of the injected 
					  event and returns the tile index
					  
		ra		   :: Right ascension of the source in degrees
		dec		   :: Declination angle of the source in degrees
		tiles	   :: The tile coordinate file (in the following format)
						ID	ra_center	dec_center	
						1  24.714290	-85.938460
						2  76.142860	-85.938460
						...
		'''
		tileData = np.recfromtxt(tiles, names=True)
		Dec_tile = tileData['dec_center']
		RA_tile = tileData['ra_center']
		ID = tileData['ID']
		s = np.arccos( np.sin(np.pi*dec/180.)\
			* np.sin(np.pi*Dec_tile/180.)\
			+ np.cos(np.pi*dec/180.)\
			* np.cos(np.pi*Dec_tile/180.) \
			* np.cos(np.pi*(RA_tile - ra)/180.) )
		index = np.argmin(s) ### minimum angular distance index

		return ID[index] - 1 ### Since the indexing begins with 1.

	
	def searchedArea(self, ra, dec, resolution=None):
		'''
		METHOD     :: This method takes the position of the injected 
					  event and the sky-map. It returns the searched 
					  area of the sky-map to reach to the source lo-
					  cation. The searched area constitutes both the
					  total area (sq. deg) that needed to be search-
					  ed to reach the source location, and the total
					  localization probability covered in the proce-
					  ss.
					  
		ra		   :: Right ascension of the source in degrees
		dec		   :: Declination angle of the source in degrees
		resolution :: The value of the nside, if not supplied, 
					  the default skymap is used.
		'''
		if not resolution:
			resolution = self.nside
		n = np.log(resolution)/np.log(2)
		resolution = int(2 ** round(n)) ## resolution in powers of 2
		if resolution > 2048: resolution = 2048
		if resolution < 64: resolution = 64
		filename = self.preCompDictFiles[resolution]
		File = open(filename, 'rb')
		data = pickle.load(File)
		tile_index = np.arange(len(data))
		skymapUD = hp.ud_grade(self.skymap, resolution, power=-2)
		npix = len(skymapUD)
		theta, phi = hp.pix2ang(resolution, np.arange(0, npix))
		ra_map = np.rad2deg(phi) # Construct ra array
		dec_map = np.rad2deg(0.5*np.pi - theta) # Construct dec array
		pVal = skymapUD[np.arange(0, npix)]
		order = np.argsort(-pVal)
		ra_map = ra_map[order]
		dec_map = dec_map[order]
		pVal = pVal[order]
		s = np.arccos( np.sin(np.pi*dec/180.)\
			* np.sin(np.pi*dec_map/180.)\
			+ np.cos(np.pi*dec/180.)\
			* np.cos(np.pi*dec_map/180.) \
			* np.cos(np.pi*(ra_map - ra)/180.) )
		index = np.argmin(s) ### minimum angular distance index
		coveredProb = np.sum(pVal[0:index])
		searchedArea = index*hp.nside2pixarea(resolution, degrees=True)
		return [searchedArea, coveredProb]

	
	def ZTF_RT(self, resolution=None, verbose=False):
		'''
		METHOD		:: This method returns two numpy arrays, the first
					   contains the tile indeces of ZTF and the second
					   contains the probability values of the corresp-
					   onding tiles. The tiles are sorted based on th-
					   eir probability values.
		
		resolution  :: The value of the nside, if not supplied, 
					   the default skymap is used.
		'''
		if not resolution:
			resolution = self.nside
		n = np.log(resolution)/np.log(2)
		resolution = int(2 ** round(n)) ## resolution in powers of 2
		if resolution > 2048: resolution = 2048
		if resolution < 64: resolution = 64
		if verbose: print 'Using resolution of ' + str(resolution)
		filename = self.preCompDictFiles[resolution]
		if verbose: print filename
		File = open(filename, 'rb')
		data = pickle.load(File)
		tile_index = np.arange(len(data))
		skymapUD = hp.ud_grade(self.skymap, resolution, power=-2)
		npix = len(skymapUD)
		theta, phi = hp.pix2ang(resolution, np.arange(0, npix))
		pVal = skymapUD[np.arange(0, npix)]

		allTiles_probs = []
		for ii in range(0, len(data)):
			pTile = np.sum(pVal[data[ii]])
			allTiles_probs.append(pTile)

		allTiles_probs = np.array(allTiles_probs)
		index = np.argsort(-allTiles_probs)

		allTiles_probs_sorted = allTiles_probs[index]
		tile_index_sorted = tile_index[index]

		
		return [tile_index_sorted, allTiles_probs_sorted]


	def plot(self, tiles, ra, dec, resolution=None, CI=0.9):
		tileData = np.recfromtxt(tiles, names=True)
		ra_center = tileData['ra_center']
		dec_center = tileData['dec_center']

		if not resolution:
			resolution = self.nside
		n = np.log(resolution)/np.log(2)
		resolution = int(2 ** round(n)) ## resolution in powers of 2
		if resolution > 2048: resolution = 2048
		if resolution < 64: resolution = 64
		print 'Using resolution of ' + str(resolution)
		skymapUD = hp.ud_grade(self.skymap, resolution, power=-2)
		hp.mollview(skymapUD)
		hp.visufunc.projplot(dec_center, ra_center,  'c.', lonlat=True)
		hp.visufunc.projplot(ra, dec,  'r*', markersize=10, lonlat=True)
		pl.show()



	def rankGalaxies2D(self, catalog, resolution=None):
		'''
		METHOD  :: This method takes as input a galaxy catalog pickle file
				   that is generated by running the createCatalog.py script.
				   The output is the IDs of the galaxies from the catalog 
				   ranked based on their localization probability.
		
		catalog	:: A pickle file which stores a 7 col numpy array with. The 
				   columns of this array are defined below:
				   		col1 : galaxy ID
				   		col2 : distance to the galaxy
				   		col3 : Declination angle of the galaxy
				   		col4 : Right ascencion of the galaxy
				   		col5 : Closest BAYESTAR Healpix pixel to the galaxy
				   		col6 : Declination angle of the closest pixel
				   		col7 : Right ascencion of the closest pixel
				   		
		resolution :: Optional argument. allows you to fix the resolution of 
					  the skymap. Currently the catalog file has only been 
					  generated for resolution of 512. Use this value.
				   
		'''

		if not resolution:
			resolution = self.nside
		n = np.log(resolution)/np.log(2)
		resolution = int(2 ** round(n)) ## resolution in powers of 2
		if resolution > 2048: resolution = 2048
		if resolution < 64: resolution = 64
		filename = self.preCompDictFiles[resolution]
		File = open(filename, 'rb')
		data = pickle.load(File)
		tile_index = np.arange(len(data))
		skymapUD = hp.ud_grade(self.skymap, resolution, power=-2)
		npix = len(skymapUD)
		theta, phi = hp.pix2ang(resolution, np.arange(0, npix))
		ra_map = np.rad2deg(phi) # Construct ra array
		dec_map = np.rad2deg(0.5*np.pi - theta) # Construct dec array
		pVal = skymapUD[np.arange(0, npix)]
		
		catalogFile = open(catalog, 'rb')
		catalogData = pickle.load(catalogFile)
		
		indices = catalogData[:,4].astype('int') ### Indices of pixels for all galaxies
		galaxy_probs = pVal[indices] ### Probability values of the galaxies in catalog
		order = np.argsort(-galaxy_probs) ### Sorting in descending order of probability
		galaxy_indices = catalogData[:,0].astype('int') ### Indices of galaxies
		ranked_galaxies = galaxy_indices[order]
		galaxy_probs = galaxy_probs[order]
		
		return [ranked_galaxies, galaxy_probs]

	def integrationTime(self, T_obs, pValTiles=None):
		'''
		METHOD :: This method accepts the probability values of the ranked tiles, the 
			  total observation time and the rank of the source tile. It returns 
			  the array of time to be spent in each tile which is determined based
			  on the localizaton probability of the tile. 
				  
		pValTiles :: The probability value of the ranked tiles. Obtained from ZTF_RT 
					 output
		T_obs     :: Total observation time available for the follow-up.
		'''
		if pValTiles is None:
			pValTiles = self.allTiles_probs_sorted
		t_tiles = pValTiles * T_obs ### Time spent in each tile if not constrained
		t_tiles[t_tiles > 1200.0] = 1200.0 ### Upper limit of exposure time
		t_tiles[t_tiles < 60] = 60.0 ### Lower limit of exposure time
		Obs = np.cumsum(t_tiles) <= T_obs ### Tiles observable in T_obs seconds
		time_per_tile = t_tiles[Obs] ### Actual time spent per tile
		
		return time_per_tile
	
	
############ UNDER CONSTRUCTION ############
	
class Scheduler(RankedTileGenerator):
	'''
	The scheduler class: Inherits from the RankedTileGenerator class. If no attribute 
	is supplied while creating schedular objects, a default instance of ZTF scheduler 
	is created. To generate scheduler for other telescopes use the corresponding site
	names which can be obtaine from astropy.coordinates.EarthLocation.get_site_names().
	The tile tile coordinate file also needs to be supplied to the variable tileCoord.
	This file needs to have at least three columns, the first being an ID (1, 2, ...),
	the second should be the tile center's ra value and the third the dec value of the 
	same. The utcoffset is the time difference between UTC and the site in hours. 
	'''
	def __init__(self, skymapFile, site='Palomar', 
				 tileCoord='ZTF_tiles_set1_nowrap_indexed.dat', utcoffset = -7.0):

		self.Observatory = EarthLocation.of_site(site)
		tileData = np.recfromtxt(tileCoord, names=True)
		self.skymapfile = skymapFile
		
		tileObj = RankedTileGenerator(skymapFile)
		[self.tileIndices, self.tileProbs] = tileObj.ZTF_RT()

		self.tiles = SkyCoord(ra = tileData['ra_center'][self.tileIndices]*u.degree, 
					    dec = tileData['dec_center'][self.tileIndices]*u.degree, 
					    frame = 'icrs') ### Tile(s)
		self.utcoffset = utcoffset*u.hour
		

	def tileVisibility(self, t, gps=False):
		'''
		METHOD	:: This method takes as input the time (gps or mjd) of observation
				   and the observatory site name, and returns the alt and az of the 
				   ranked tiles. It also returns the alt and az of the sun.
		t	    :: The time at which observation is made. Default is mjd. If time is 
				   given in gps then set gps to True.

		'''
		if gps: time = Time(t, format='gps') ### If time is given in GPS format
		else: time = Time(t, format='mjd') ### else time is assumed in mjd format
		altAz_tile = self.tiles.transform_to(AltAz(obstime=time, location=self.Observatory))
		altAz_sun = get_sun(time).transform_to(AltAz(obstime=time, location=self.Observatory))
		
		isSunDown = altAz_sun.alt.value < -18.0 ### Checks if it is past twilight.
		whichTilesUp = altAz_tile.alt.value > 20.0  ### Checks which tiles are up		
		
# 		return [altAz_tile, self.tileProbs, altAz_sun]
		return [self.tileIndices[whichTilesUp], self.tileProbs[whichTilesUp], altAz_sun]
		
		
	def observationSchedule(self, duration, eventTime, integrationTime=120,
							observedTiles=None, plot=False, verbose=False):
		'''
		METHOD	:: This method takes the duration of observation, time of the GW trigger
				   integration time per tile as input and outputs the observation
				   schedule.
				   
		duration   		 :: Total duration of the observation in seconds.
		eventTime  		 :: The gps time of the time of the GW trigger.
		integrationTime  :: Time spent per tile in seconds (default == 120 seconds)
		observedTiles	 :: (Future development) Array of tile indices that has been 
							observed in n earlier epoch
		plot			 :: (optional) Plots the tile centers that are observed.
		verbose			 :: Toggle verbose flag for print statements.
				   
		
		'''
		
		if plot:
			from AllSkyMap_basic import AllSkyMap
			
						

		observedTime = 0 ## Initiating the observed times
		scheduled = np.array([]) ## tile indices scheduled for observation
		ObsTimes = []
		pVal_observed = []
		ii = 0
		observed_count = 0
		while observedTime <= duration:
			dt = integrationTime * ii
			[tileIndices, tileProbs, altAz_sun] = self.tileVisibility(eventTime + dt,
																		 gps=True)
			localTime = Time(eventTime + dt, format='gps') + self.utcoffset
			
			if altAz_sun.alt.value < -18.0: ### Sun below horizon
				observed_count += 1
				observedTime += integrationTime ### Augment observed time
				if verbose: 
					print str(localTime.utc.datetime) + ': Observation mode'

				for jj in np.arange(len(tileIndices)):
					if tileIndices[jj] not in scheduled:
					#if ~np.in1d(tileIndices[jj], scheduled):
						scheduled = np.append(scheduled, tileIndices[jj])
						ObsTimes.append(localTime)
						pVal_observed.append(tileProbs[jj])
						break

			else:
				if verbose: print str(localTime.utc.datetime) + ': Sun above the horizon'
			
			ii += 1
		for ii in np.arange(len(scheduled)):
			print str(ObsTimes[ii].utc.datetime) + '\t' + str(int(scheduled[ii]))
			
		return [scheduled.astype('int'), pVal_observed]

				










####################END OF CLASS METHODS########################


def evolve_abs_Mag(dt, model, offset=0):	### UNDERDEVELOPMENT ###
	'''
	METHOD	:: This method takes as input the light curve model and the time
			   since the merger and outputs the absolute magnitude of the 
			   source.
			   
	dt 	 	:: Time since merger
	model	:: The light curve model. Right now only one model (NSNS_MNmodel1_FRDM_r)
	offset	:: (Optional) The offset of the peak of the light curve from the merger.
	'''

	data = np.recfromtxt(model, names=True)
	s = interpolate.UnivariateSpline(data['time'], data['magnitude'], k=5)
	mag = s(dt - offset)

	
def gaussian_distribution_function(x, mu, sigma):
		'''
		METHOD	:: Creates the gaussian function corresponding to the
				   mean and standard deviation of the limiting magnitude
				   corresponding to the given time
		'''
		return 1/(np.sqrt(2*np.pi*sigma**2))*np.exp(-(x-mu)**2/(2*sigma**2))

def apparent_from_absolute_mag(absolute_mag, source_dist_parsec):
		'''
		METHOD	:: This method computes the aparent magnitude from the absolute
		magnitude model and the distance to the source.
		'''
		return absolute_mag + 5*np.log10(source_dist_parsec/10.)

def detectability(rank, time_per_tile, total_observation_time, absolute_mag, source_dist_parsec, time_data, limmag_data, error_data = None, verbose=False):
	'''
	METHOD :: This method takes as input the time allotted per tile, 
	total observation time allotted for an event, the absolute 
	magnitude model of the source and the dependence of 
	limiting magnitude on integration time, and returns either a 
	boolean numpy object[True/False] whether the source can be detected, or
	a probability of detection if the error data (sigma) for 
	the limiting magnitude is provided.
		  
	total_observation_time 	 :: The total observation time for the event
	absolute_magnitude 		 :: The absolute magnitude of the source that 
					is to be set by the model.
	source_dist_parsec 		 :: distance to source in parsecs time_data, 
					limmag_data, error_data :: The data which 
					needs to be interpolated to give limiting 
					magnitude as a function of time. error_data, 
					if provided, will allow for a detection 
					probability to be generated as output. If 
					detectability(rank, time_per_tile, total_observation_time, absolute_mag, source_dist_parsec, time_data, limmag_data, error_data = None, verbose=False)error_data is not provided, a Boolean 
					(True/False) for detection will be output. 
	'''
	### Convert to numpy object if scalar supplied
	if isinstance(time_per_tile, (np.ndarray,)) == False:
		time_per_tile = np.array(time_per_tile)
	### Check if source tile rank has been reached. Return non-detection if not
	rank_reached		= (total_observation_time/time_per_tile).astype(int)
	rank_reached_mask	= rank_reached > rank	# True means rank is reachable
	if np.all(~rank_reached_mask):	# if rank cannot be reached for 
									# any integration time	
		if verbose: print "Tile not reached in ANY allotted observation time"
		if error_data is not None:
			return np.zeros(len(time_per_tile))
		else:
			return rank_reached_mask

	### Determine limiting magnitude as a function of time, via interpolation of data
	s = interpolate.UnivariateSpline(np.log(time_data), limmag_data, k=5)
	limmag = s(np.log(time_per_tile))
	apparent_mag = apparent_from_absolute_mag(absolute_mag, source_dist_parsec)
	### If error_data is not supplied, return Boolean True/False for detection
	if error_data is None:
		depthReached = (limmag > apparent_mag)
		if np.any(depthReached) is False:
			if verbose: print "Depth not reached in ANY allotted integration time"
		return np.logical_and(depthReached, rank_reached_mask)
		### Both Depth criteria and rank criteria should be satisfied
	### If error_data is supplied, return detection probability
	else:
		s_err = interpolate.UnivariateSpline(np.log(time_data), error_data, k=5)
		mu = limmag
		sigma = s_err(np.log(time_per_tile))
		very_large_number = 1000 #proxy for +infinity
		samples = 10**5
		x = np.linspace(apparent_mag, very_large_number, samples, endpoint = True)
		### If floats are passed to the function, return the answer rightaway
		if isinstance(mu, (float, np.float, np.float64,)) == True and  isinstance(sigma, (float, np.float, np.float64,)) == True:
			y = gaussian_distribution_function(x, mu, sigma)
			return np.trapz(y,x)
		# If an array of time_per_tile had been passed
		# Note that mu and sigma are equal length arrays, as defined above
		else:
			result = []
			for ii in range(len(mu)):
				y = gaussian_distribution_function(x,mu[ii],sigma[ii])
				result.append(np.trapz(y,x))
			return np.array(result)
