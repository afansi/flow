# flake8: noqa
"""Script to load an Aimsun instance from a template."""
import os
import os.path as osp
import json
import sys

if len(sys.argv) > 2:
    PROJECT_PATH = sys.argv[2]
else:
    raise ValueError("Project Path is not Defined")

try:
    AIMSUN_SITEPACKAGES = os.environ.get("AIMSUN_SITEPACKAGES", None)
    SITEPACKAGES = osp.join(AIMSUN_SITEPACKAGES, "lib/python2.7/site-packages")
    sys.path.append(SITEPACKAGES)
except TypeError:
    raise EnvironmentError("Please declare the AIMSUN_SITEPACKAGES environment variable.")

class AimsunTemplate(object):
    """Interface to do scripting with Aimsun.

    This can be used to create Aimsun templates or to load and modify existing
    ones. It provides a pythonic interface to manipulate the different objects
    accessible via scripting.
    """

    def __init__(self, GKSystem, GKGUISystem):
        """Initialize the template.

        This assumes that Aimsun is open, as it will try to access the
        current active Aimsun window.

        After that, this class provides different methods to manipulate
        templates in this Aimsun window:
        (1) to load a template, see 'load_template'
        (2) to create a new template by duplicating an existing one, see
            'duplicate_template'
        (3) to create a new blank template, see 'new_template'
        (4) if the template you want to use is already open in the Aimsun
            window, then you don't have to do annything

        In cases (2) and (3), see 'save' to then save the template.

        Parameters
        ----------
        GKSystem : GKSystem (Aimsun singleton class)
            Aimsun's GKSystem object
        GKGUISystem : GKGUISystem (Aimsun singleton class)
            Aimsun's GKGUISystem object

        Note
        ----
        This class takes as parameter the two high-level objects provided
        when interfacing with Aimsun: GKSystem and GKGUISystem. After having
        imported this class, you should be able to create an AimsunTemplate
        object as follows:

            model = AimsunTemplate(GKSystem, GKGUISystem)
        """
        self.GKSystem = GKSystem
        self.GKGUISystem = GKGUISystem

        self.gui = self.GKGUISystem.getGUISystem().getActiveGui()
        self.model = self.gui.getActiveModel()

    def load(self, path):
        """Load an existing template into Aimsun.

        Parameters
        ----------
        path : str
            the path of the template to load
        """
        self.gui.loadNetwork(path)
        self.model = self.gui.getActiveModel()
        self.__wrap_object(self.model)

    def new_duplicate(self, path):
        """Create a new template by duplicating an existing one.

        Parameters
        ----------
        path : str
            the path of the template to be duplicated
        """
        self.gui.newDoc(path)
        self.model = self.gui.getActiveModel()
        self.__wrap_object(self.model)

    def new_empty(self):
        """Create a new empty template."""
        self.gui.newSimpleDoc()
        self.model = self.gui.getActiveModel()
        self.__wrap_object(self.model)

    def save(self, path):
        """Save the current template.

        Parameters
        ----------
        path : str
            the path where the current active template should be saved
        """
        self.gui.saveAs(path)

    def run_replication(self, replication, render=True):
        """Run a replication in Aimsun.

        Parameters
        ----------
        replication : GKReplication
            the replication to be run; you can access the list of all available
            GKReplication objects by doing model.replications where
            model is an instance of the AimsunTemplate class.
        render : bool (default: True)
            whether or not the simulation should be rendered
        """
        # "play": run with GUI; "execute": run in batch mode
        mode = 'play' if render else 'execute'
        self.GKSystem.getSystem().executeAction(mode, replication, [], "")

    ####################################################################
    #                Methods to retrieve Aimsun objects                #
    ####################################################################

    def __getattr__(self, name):
        """Return object attribute.

        If trying to access an attribute in this AimsunTemplate object
        fails, try to access it into the Aimsun model object

        Parameters
        ----------
        name : str
            name of the attribute to be retrieved
        """
        return getattr(self.model, name)

    def __wrap_object(self, obj):
        """Wrap Aimsun objects with custom __getattr__ and __setattr__ methods.

        This provides a more pythonic attribute access and attribute
        modification.

        Parameters
        ----------
        obj : GKObject (Aimsun class)
            the object to wrap

        Examples of what this method does:
        - s.getSpeed() becomes s.speed
        - t.getDestination().getName() becomes t.destination.name
        - t.getPolygon().length2D() becomes t.polygon.length2D()
        - exp.setDataValue(model.getColumn(...), ...) becomes
          exp.set_data_value(model.get_column(...), ...)
        - s.setName(new_name) becomes s.name = new_name
        etc.

        Notes
        -----
        - This method directly modifies the object and does not return anything
        - For back-compatibility, it is still possible to call the original
          Aimsun methods
        """
        if obj is None:
            return

        # custom capitalize function that doesn't lowercase the suffix
        def capitalize(str):
            return str[0].upper() + str[1:]

        outer_self = self

        def custom_getattr(self, name):
            # transform name from attr_name to AttrName
            name = ''.join(map(capitalize, name.split('_')))

            # attempt to retrieve getAttrName, or attrName if the first fails
            name1 = 'get' + name
            name2 = name[0].lower() + name[1:]
            try:
                aimsun_fct = object.__getattribute__(self, name1)
            except AttributeError:
                try:
                    aimsun_fct = object.__getattribute__(self, name2)
                except AttributeError:
                    # if both attempts fail, raise an AttributeError with
                    # the original attribute name (instead of name1 or name2)
                    raise AttributeError(
                        '\'{}\' has no attribute \'{}\''.format(
                            self.__class__.__name__, name))

            # call the Aimsun function (which most likely is a getter)
            try:
                result = aimsun_fct()
            except TypeError:
                # if it is not a function, just return the attribute
                result = aimsun_fct

            # wrap whatever object the getter returns, so that we can access
            # deeper attributes (e.g. turning.destination.name)
            try:
                if type(result) is list:
                    map(outer_self.__wrap_object, result)
                else:
                    outer_self.__wrap_object(result)
            except TypeError:
                # we can't wrap a basic type like int; ignore the exception
                pass

            return result

        # assign this custom __getattr__ function to the object
        # note that it will only be called if __getattribute__ fails,
        # so we can still call the original Aimsun functions like s.getName()
        obj.__class__.__getattr__ = custom_getattr

        def custom_setattr(self, name, value):
            try:
                # transform name from attr_name to setAttrName
                aimsun_name = 'set' + ''.join(map(capitalize, name.split('_')))
                # retrieve the Aimsun setter
                aimsun_setter = object.__getattribute__(self, aimsun_name)
                # call the setter to set the new value to attribute 'name'
                aimsun_setter(value)
            except AttributeError:
                # if we couldn't retrieve an Aimsun setter, we set the
                # attribute manually
                object.__setattr__(self, name, value)
            return value

        # assign this custom __setattr__ function to the object
        obj.__class__.__setattr__ = custom_setattr

    def __wrap_objects(self, objects):
        """See __wrap_object.

        Parameters
        ----------
        objects : GKObject (Aimsun class) list
            list of objects to wrap (IMPORTANT: all the objects in the list
            must be of the same type)
        """
        map(self.__wrap_object, objects)

    def __get_objects_by_type(self, type_name):
        """Simplify getter for Aimsun objects.

        Parameters
        ----------
        type_name : str

        Returns
        -------
        GKObject (Aimsun class) list
            list of all Aimsun objects whose type is type_name
        """
        type_obj = self.model.getType(type_name)
        objects = self.model.getCatalog().getObjectsByType(type_obj).values()
        self.__wrap_objects(objects)
        return objects

    def find_by_name(self, objects, name):
        """Find an Aimsun object by its name.

        Parameters
        ----------
        objects : GKObject (Aimsun type) list
            list of objects to search into
        name : str
            name of the object to look for

        Returns
        -------
        the first object in the list 'objects' whose name is 'name'
        """
        matches = (obj for obj in objects if obj.getName() == name)
        ret = next(matches, None)
        self.__wrap_object(ret)
        return ret

    def find_all_by_type(self, objects, type_name):
        """Find Aimsun objects by their type.

        Parameters
        ----------
        objects : GKObject (Aimsun type) list
            list of objects to search into
        type_name : str
            name of the type to look for

        Returns
        -------
        all objects in the list 'objects' whose type's name is 'type_name'
        """
        matches = [obj for obj in objects if obj.getTypeName() == type_name]
        self.__wrap_objects(matches)
        return matches

    @property
    def sections(self):
        """Return Aimsun GKSection attribute.

        A section is a group of contiguous lanes where vehicles move in the
        same direction. The partition of the traffic network into sections is
        usually governed by the physical boundaries of the area and the
        existence of turn movements. In an urban network, a section corresponds
        closely to the road from one intersection to the next. In a freeway
        area, a section can be the part of the road between two ramps.
        """
        return self.__get_objects_by_type('GKSection')

    @property
    def nodes(self):
        """Return Aimsun GKTurning attribute.

        A node is a point or an area in the network where vehicles change their
        direction and/or disperse. Hence, a node has one or more origin
        sections and one or more destination sections. Each node has a turns
        list, which determines the possible exits of a vehicle entering the
        nodes.
        """
        return self.__get_objects_by_type('GKNode')

    @property
    def turnings(self):
        """Return Aimsun GKSection attribute.

        This object is responsible for connecting some (or all) lanes between
        two sections.
        """
        return self.__get_objects_by_type('GKTurning')

    @property
    def cen_connections(self):
        """Return Aimsun GKCenConnection attribute.

        This contains information of a connection between an object and a
        centroid.
        """
        return self.__get_objects_by_type('GKCenConnection')

    @property
    def replications(self):
        """Return Aimsun GKReplication attribute.

        A replication used by the Aimsun Next Simulators. They are the result
        of a single simulation and they are groupped in experiment averages
        (GKExperimentResult).
        """
        return self.__get_objects_by_type('GKReplication')

    @property
    def centroid_configurations(self):
        """Return Aimsun GKCentroidConfiguration attribute.

        This object is a centroid set, which is appropriate to simulate either
        a part of the network or the whole network.
        """
        return self.__get_objects_by_type('GKCentroidConfiguration')

    @property
    def problem_nets(self):
        """Return Aimsun GKProblemNet attribute.

        A subnetwork is an area in a (very large) network that will be studied
        with more detail using a dynamic simulator (usually a micro one).

        The area is selected either as a polygon or as a set of sections. From
        that information is possible to extract all the objects delimited by
        the subnetwork.
        """
        return self.__get_objects_by_type('GKProblemNet')


def load_network(model):
    """Load the whole network into a dictionary and returns it."""
    sections = model.sections
    nodes = model.nodes
    turnings = model.turnings
    cen_connections = model.cen_connections

    scenario_data = get_dict_from_objects(sections, nodes, turnings,
                                          cen_connections)
    return scenario_data


def load_subnetwork(subnetwork, scenario):
    """Load subnetwork into a dictionary and returns it."""
    # get all objects in subnetwork
    objs = list(subnetwork.classify_objects(scenario.id))

    sections = model.find_all_by_type(objs, 'GKSection')
    nodes = model.find_all_by_type(objs, 'GKNode')
    turnings = model.find_all_by_type(objs, 'GKTurning')
    cen_connections = model.find_all_by_type(objs, 'GKCenConnection')

    scenario_data = get_dict_from_objects(sections, nodes, turnings,
                                          cen_connections)
    return scenario_data


def get_dict_from_objects(sections, nodes, turnings, cen_connections):
    """Load all relevant data into dictionaries."""
    scenario_data = {
        'sections': {},
        'nodes': {},
        'turnings': {},
        'centroids': {},
        'connections': {}
    }

    # load centroids
    # TODO use centroids when we don't have a centroid configuration
    # centroids = [o for o in objs if o.getTypeName() == 'GKCentroid']
    # FIXME doesn't handle centroids that are both in and out
    # maybe no need to distinguish them since it is done
    # later with centroid connections
    centroid_config_name = data['centroid_config_name']
    centroid_config = model.find_by_name(model.centroid_configurations,
                                         centroid_config_name)
    if not centroid_config:
        print('[load.py] ERROR: Centroid configuration ' +
              centroid_config_name + ' does not exist.')
    else:
        # load origin centroids only if they exist
        if centroid_config.origin_centroids:
            for c in centroid_config.origin_centroids:
                scenario_data['centroids'][c.id] = {'type': 'in'}

        # load destination centroids only if they exist
        if centroid_config.destination_centroids:
            for c in centroid_config.destination_centroids:
                scenario_data['centroids'][c.id] = {'type': 'out'}

    # load sections
    for s in sections:
        scenario_data['sections'][s.id] = {
            'name': s.name,
            'numLanes': s.nb_full_lanes,
            'length': s.length2D(),
            'speed': s.speed
        }

    # load nodes
    for n in nodes:
        scenario_data['nodes'][n.id] = {
            'name': n.name,
            'nb_turnings': len(n.turnings)
        }

    # load turnings
    for t in turnings:
        scenario_data['turnings'][t.id] = {
            'name': t.name,
            'length': t.polygon.length2D() / 2,  # FIXME not totally accurate
            'origin_section_name': t.origin.name,
            'origin_section_id': t.origin.id,
            'dest_section_name': t.destination.name,
            'dest_section_id': t.destination.id,
            'node_id': t.node.id,
            'max_speed': t.speed,
            'origin_from_lane': t.origin_from_lane,
            'origin_to_lane': t.origin_to_lane,
            'dest_from_lane': t.destination_from_lane,
            'dest_to_lane': t.destination_to_lane
        }

    # load centroid connections
    for c in cen_connections:
        from_id = c.owner.id
        from_name = c.owner.name
        to_id = c.connection_object.id
        to_name = c.connection_object.name

        # invert from and to if connection is reversed
        if c.connection_type == 1:  # TODO verify this
            from_id, to_id = to_id, from_id
            from_name, to_name = to_name, from_name

        scenario_data['connections'][c.id] = {
            'from_id': from_id,
            'from_name': from_name,
            'to_id': to_id,
            'to_name': to_name
        }

    return scenario_data

port_string = sys.argv[1]

# collect template path
file_path = osp.join(PROJECT_PATH,
                         'flow/utils/aimsun/aimsun_template_path_%s'%port_string)
with open(file_path, 'r') as f:
    template_path = f.readline()
os.remove(file_path)

# open template in Aimsun
print('[load.py] Loading template ' + template_path)
model = AimsunTemplate(GKSystem, GKGUISystem)
model.load(template_path)

# HACK: Store port in author
model.setAuthor(port_string)

# collect the simulation parameters
params_file = 'flow/core/kernel/network/data_%s.json' % port_string
params_path = osp.join(PROJECT_PATH, params_file)
with open(params_path) as f:
    data = json.load(f)

# retrieve replication by name
replication_name = data['replication_name']
replication = model.find_by_name(model.replications, replication_name)

if replication is None:
    print('[load.py] ERROR: Replication ' + replication_name +
          ' does not exist.')

# retrieve experiment and scenario
experiment = replication.experiment
scenario = experiment.scenario
scenario_data = scenario.input_data
scenario_data.add_extension(osp.join(
    PROJECT_PATH, 'flow/utils/aimsun/test_run.py'), True)

# if subnetwork_name was specified in the Aimsun params,
# try to only load subnetwork; it not specified or if
# subnetwork is not found, load the whole network
subnetwork_name = data['subnetwork_name']
if subnetwork_name is not None:
    subnetwork = model.find_by_name(model.problem_nets, subnetwork_name)
    if subnetwork:
        scenario_data = load_subnetwork(subnetwork, scenario)
    else:
        print('[load.py] ERROR: Subnetwork ' + subnetwork_name +
              ' could not be found. Loading the whole network.')
        scenario_data = load_network(model)
else:
    scenario_data = load_network(model)

# save template's scenario into a file to be loaded into Flow's scenario
scenario_data_file = 'flow/core/kernel/network/network_data_%s.json'%port_string
scenario_data_path = osp.join(PROJECT_PATH, scenario_data_file)
with open(scenario_data_path, 'w') as f:
    json.dump(scenario_data, f, sort_keys=True, indent=4)
    print('[load.py] Template\'s scenario data written into ' +
          scenario_data_path)

# create a check file to announce that we are done
# writing all the network data into the .json file
check_file = 'flow/core/kernel/network/network_data_check_%s'%port_string
check_file_path = osp.join(PROJECT_PATH, check_file)
open(check_file_path, 'a').close()

# get simulation step attribute column
col_sim = model.get_column('GKExperiment::simStepAtt')
# set new simulation step value
experiment.set_data_value(col_sim, data['sim_step'])
# run the simulation
model.run_replication(replication=replication, render=data['render'])
