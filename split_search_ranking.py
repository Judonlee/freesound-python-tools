import manager
import sys
from sklearn import cluster
import webbrowser
import functools

def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)

sentinel = object()
def rgetattr(obj, attr, default=sentinel):
    if default is sentinel:
        _getattr = getattr
    else:
        def _getattr(obj, name):
            return getattr(obj, name, default)
    return functools.reduce(_getattr, [obj]+attr.split('.'))


class SplitSearch():
    def __init__(self, query, descriptor):
        self.c = manager.Client()
        self.query = query
        self.descriptor_name = descriptor # TODO : A way to load several descriptor
        
    def search(self):
        """Query to Freesound api, load sounds and analysis stats into a Basket"""
        self.rep = self.c.my_text_search(query=self.query, fields='id,name,tags,analysis', descriptors=self.descriptor_name)
        self.b = self.c.new_basket()
        self.b.load_sounds_(self.rep)
        #self.b.add_analysis_stats()
        
    def extract_descriptors(self):
        # Create arrays of descriptors and Freesound sound ids ; remove sounds that do not have analysis stats
        self.descriptor = []
        self.sound_ids = []
        self.sound_ids_no_stats = []
        self.sound_ids_to_remove = []
        for idx, item in enumerate(self.b.analysis_stats):
            if item:
                self.descriptor.append(rgetattr(item, self.descriptor_name))
                self.sound_ids.append(self.b.sounds[idx].id)
            else:
                self.sound_ids_no_stats.append(self.b.sounds[idx].id)
                self.sound_ids_to_remove.append(idx)
        
        # Create a Basket with only sounds that have analysis stats 
        self.b_refined = self.b
        self.b_refined.remove(self.sound_ids_to_remove)

        # Ensure that the dimension of the descriptor is NxK with N:nb data, K=dim
        if not isinstance(self.descriptor[0], list):
            self.descriptor = [[i] for i in self.descriptor]
                
    def get_descriptors(self, scale=False):
        self.descriptor = []
        self.sound_ids = []
        self.sound_ids_to_remove = []
        for idx, item in enumerate(self.b.analysis_stats):
            if item:
                self.sound_ids.append(self.b.sounds[idx].id)
            else:
                self.sound_ids_to_remove.append(idx)
        
        # Create a Basket with only sounds that have analysis stats 
        self.b_refined = self.b
        self.b_refined.remove(self.sound_ids_to_remove)
        # Extract descriptors stats
        self.descriptor = self.b_refined.extract_descriptor_stats(scale=scale)

    def cluster(self, nb_cluster):
        """Aplly kmeans clustering"""
        self.kmeans = cluster.KMeans(n_clusters=nb_cluster)
        self.kmeans.fit(self.descriptor)
        self.clas = self.kmeans.fit_predict(self.descriptor) 
        
        # Get Freesound sound ids in relevance order and create the cluster Baskets
        self.list_baskets = [self.c.new_basket() for i in range(nb_cluster)]
        self.list_clas_ids = [[] for i in range(nb_cluster)]
        for idx, item in enumerate(self.clas):
            self.list_baskets[item].push(self.b_refined.sounds[idx])
            self.list_clas_ids[item].append(self.sound_ids[idx])
        
    def get_tags(self):
        """Get the normalized tag number of occurrences"""
        # TODO : COUNT OCCURRENCES OF TAGS IN DESCRIPTIONS ALSO
        tags_occurrences = [basket.tags_occurrences() for basket in self.list_baskets]
        self.normalized_tags_occurrences = []
        for idx, tag_occurrence in enumerate(tags_occurrences):
            self.normalized_tags_occurrences.append([(t_o[0], float(t_o[1])/len(self.list_baskets[idx].sounds)) for t_o in tag_occurrence])
    
    def print_basket(self, num_basket, max_tag = 100):
        """Print tag occurrences"""
        print '\n'
        for idx, tag in enumerate(self.normalized_tags_occurrences[num_basket]):
            if idx < max_tag:
                print tag[0].ljust(30) + str(tag[1])[0:5]
            else:
                break
    
    def create_html_for_cluster(self, num_cluster):
        """Create a html with the Freesound embed"""
        # This list contains the begining and the end of the embed
        # Need to insert the id of the sound
        embed_blocks = ['<iframe frameborder="0" scrolling="no" src="https://www.freesound.org/embed/sound/iframe/', '/simple/medium/" width="481" height="86"></iframe>']
        
        # Create the html string
        message = """
        <html>
            <head></head>
            <body>
        """
        for idx, ids in enumerate(self.list_baskets[num_cluster].ids):
            message += embed_blocks[0] + str(ids) + embed_blocks[1]
            if idx > 50:
                break
        message += """
            </body>
        </html>
        """

        # Create the file
        f = open('result_cluster'+ str(num_cluster) +'.html', 'w')
        f.write(message)
        f.close()
        
        # Open it im the browser
        webbrowser.open_new_tab('result_cluster'+ str(num_cluster) +'.html')
    
    
if __name__ == '__main__':
    query = sys.argv[1]
    nb_cluster = int(sys.argv[2])
    #descriptor = 'lowlevel.mfcc.var,sfx.inharmonicity.mean'#'lowlevel.barkbands.mean'
    descriptor = 'lowlevel.gfcc.mean,lowlevel.gfcc.var,lowlevel.spectral_energyband_high.min,lowlevel.spectral_energyband_high.max,lowlevel.spectral_energyband_high.dvar2,lowlevel.spectral_energyband_high.dmean2,lowlevel.spectral_energyband_high.dmean,lowlevel.spectral_energyband_high.var,lowlevel.spectral_energyband_high.dvar,lowlevel.spectral_energyband_high.mean,lowlevel.spectral_contrast.min,lowlevel.spectral_contrast.max,lowlevel.spectral_contrast.dvar2,lowlevel.spectral_contrast.dmean2,lowlevel.spectral_contrast.dmean,lowlevel.spectral_contrast.var,lowlevel.spectral_contrast.dvar,lowlevel.spectral_contrast.mean,lowlevel.silence_rate_60dB.min,lowlevel.silence_rate_60dB.max,lowlevel.silence_rate_60dB.dvar2,lowlevel.silence_rate_60dB.dmean2,lowlevel.silence_rate_60dB.dmean,lowlevel.silence_rate_60dB.var,lowlevel.silence_rate_60dB.dvar,lowlevel.silence_rate_60dB.mean,lowlevel.spectral_centroid.min,lowlevel.spectral_centroid.max,lowlevel.spectral_centroid.dvar2,lowlevel.spectral_centroid.dmean2,lowlevel.spectral_centroid.dmean,lowlevel.spectral_centroid.var,lowlevel.spectral_centroid.dvar,lowlevel.spectral_centroid.mean,lowlevel.spectral_complexity.min,lowlevel.spectral_complexity.max,lowlevel.spectral_complexity.dvar2,lowlevel.spectral_complexity.dmean2,lowlevel.spectral_complexity.dmean,lowlevel.spectral_complexity.var,lowlevel.spectral_complexity.dvar,lowlevel.spectral_complexity.mean,lowlevel.spectral_crest.min,lowlevel.spectral_crest.max,lowlevel.spectral_crest.dvar2,lowlevel.spectral_crest.dmean2,lowlevel.spectral_crest.dmean,lowlevel.spectral_crest.var,lowlevel.spectral_crest.dvar,lowlevel.spectral_crest.mean,lowlevel.spectral_spread.min,lowlevel.spectral_spread.max,lowlevel.spectral_spread.dvar2,lowlevel.spectral_spread.dmean2,lowlevel.spectral_spread.dmean,lowlevel.spectral_spread.var,lowlevel.spectral_spread.dvar,lowlevel.spectral_spread.mean,lowlevel.spectral_contrast.min,lowlevel.spectral_contrast.max,lowlevel.spectral_contrast.dvar2,lowlevel.spectral_contrast.dmean2,lowlevel.spectral_contrast.dmean,lowlevel.spectral_contrast.var,lowlevel.spectral_contrast.dvar,lowlevel.spectral_contrast.mean,lowlevel.zerocrossingrate.min,lowlevel.zerocrossingrate.max,lowlevel.zerocrossingrate.dvar2,lowlevel.zerocrossingrate.dmean2,lowlevel.zerocrossingrate.dmean,lowlevel.zerocrossingrate.var,lowlevel.zerocrossingrate.dvar,lowlevel.zerocrossingrate.mean,sfx.inharmonicity.min,sfx.inharmonicity.max,sfx.inharmonicity.dvar2,sfx.inharmonicity.dmean2,sfx.inharmonicity.dmean,sfx.inharmonicity.var,sfx.inharmonicity.dvar,sfx.inharmonicity.mean,sfx.tristimulus.min,sfx.tristimulus.max,sfx.tristimulus.dvar2,sfx.tristimulus.dmean2,sfx.tristimulus.dmean,sfx.tristimulus.var,sfx.tristimulus.dvar,sfx.tristimulus.mean'
    #,lowlevel.spectral_flatness_db.mean,lowlevel.spectral_flatness_db.var'
    Search = SplitSearch(query, descriptor)
    Search.search()
    #Search.extract_descriptors()
    Search.get_descriptors(scale=False)
    Search.cluster(nb_cluster)
    Search.get_tags()
    for i in range(nb_cluster):
        Search.print_basket(i, 20)
        #Search.create_html_for_cluster(i)