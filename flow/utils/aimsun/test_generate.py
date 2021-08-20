# flake8: noqa
"""Script for generating a custom Aimsun network."""
# TODO adapt this file with respect to scripting_api.py

print("HELLO WORLD !")

import sys
import os
import os.path as osp
from copy import deepcopy
import json
import math
import warnings

from PyANGBasic import *
from PyANGKernel import *
from PyANGConsole import *

if len(sys.argv) > 2:
    PROJECT_PATH = sys.argv[2]
else:
    raise ValueError("Project Path is not Defined")

AIMSUN_SITEPACKAGES = os.environ.get("AIMSUN_SITEPACKAGES", None)

# path to the Aimsun_Next main directory (required for Aimsun simulations)
AIMSUN_NEXT_PATH = os.environ.get("AIMSUN_NEXT_PATH", None)

SITEPACKAGES = osp.join(AIMSUN_SITEPACKAGES, "lib/python2.7/site-packages")
sys.path.append(SITEPACKAGES)

# for a in sys.path:
#     print("%s" % (a))

print("INITIALIZATION SCRIPTING")
print("SITEPACKAGES: %s" % (SITEPACKAGES))
print("config.AIMSUN_SITEPACKAGES: %s " % (AIMSUN_SITEPACKAGES))
print("config.AIMSUN_NEXT_PATH: %s" % (AIMSUN_NEXT_PATH))

sys.path.append(osp.join(AIMSUN_NEXT_PATH, 'programming/Aimsun Next API/python/private/Micro'))

def deprecated_attribute(obj, dep_from, dep_to):
    """Print a deprecation warning.
    Parameters
    ----------
    obj : class
        The class with the deprecated attribute
    dep_from : str
        old (deprecated) name of the attribute
    dep_to : str
        new name for the attribute
    """
    warnings.simplefilter('always', PendingDeprecationWarning)
    warnings.warn(
        "The attribute {} in {} is deprecated, use {} instead.".format(
            dep_from, obj.__class__.__name__, dep_to),
        PendingDeprecationWarning
    )

# Traffic light defaults
PROGRAM_ID = 1
MAX_GAP = 3.0
DETECTOR_GAP = 0.6
SHOW_DETECTORS = True

class TrafficLightParams:
    """Base traffic light.
    This class is used to place traffic lights in the network and describe
    the state of these traffic lights. In addition, this class supports
    modifying the states of certain lights via TraCI.
    """

    def __init__(self, baseline=False):
        """Instantiate base traffic light.
        Attributes
        ----------
        baseline: bool
        """
        # traffic light xml properties
        self.__tls_properties = dict()

        # all traffic light parameters are set to default baseline values
        self.baseline = baseline

    def add(self,
            node_id,
            tls_type="static",
            programID=10,
            offset=None,
            phases=None,
            maxGap=None,
            detectorGap=None,
            showDetectors=None,
            file=None,
            freq=None):
        """Add a traffic light component to the network.
        When generating networks using xml files, using this method to add a
        traffic light will explicitly place the traffic light in the requested
        node of the generated network.
        If traffic lights are not added here but are already present in the
        network (e.g. through a prebuilt net.xml file), then the traffic light
        class will identify and add them separately.
        Parameters
        ----------
        node_id : str
            name of the node with traffic lights
        tls_type : str, optional
            type of the traffic light (see Note)
        programID : str, optional
            id of the traffic light program (see Note)
        offset : int, optional
            initial time offset of the program
        phases : list  of dict, optional
            list of phases to be followed by the traffic light, defaults
            to default sumo traffic light behavior. Each element in the list
            must consist of a dict with two keys:
            * "duration": length of the current phase cycle (in sec)
            * "state": string consist the sequence of states in the phase
            * "minDur": optional
                The minimum duration of the phase when using type actuated
            * "maxDur": optional
                The maximum duration of the phase when using type actuated
        maxGap : int, optional
            describes the maximum time gap between successive vehicle that will
            cause the current phase to be prolonged, **used for actuated
            traffic lights**
        detectorGap : int, optional
            used for actuated traffic lights
            determines the time distance between the (automatically generated)
            detector and the stop line in seconds (at each lanes maximum
            speed), **used for actuated traffic lights**
        showDetectors : bool, optional
            toggles whether or not detectors are shown in sumo-gui, **used for
            actuated traffic lights**
        file : str, optional
            which file the detector shall write results into
        freq : int, optional
            the period over which collected values shall be aggregated
        Note
        ----
        For information on defining traffic light properties, see:
        http://sumo.dlr.de/wiki/Simulation/Traffic_Lights#Defining_New_TLS-Programs
        """
        # prepare the data needed to generate xml files
        self.__tls_properties[node_id] = {"id": node_id, "type": tls_type}

        if programID:
            self.__tls_properties[node_id]["programID"] = programID

        if offset:
            self.__tls_properties[node_id]["offset"] = offset

        if phases:
            self.__tls_properties[node_id]["phases"] = phases

        if tls_type == "actuated":
            # Required parameters
            self.__tls_properties[node_id]["max-gap"] = \
                maxGap if maxGap else MAX_GAP
            self.__tls_properties[node_id]["detector-gap"] = \
                detectorGap if detectorGap else DETECTOR_GAP
            self.__tls_properties[node_id]["show-detectors"] = \
                showDetectors if showDetectors else SHOW_DETECTORS

            # Optional parameters
            if file:
                self.__tls_properties[node_id]["file"] = file

            if freq:
                self.__tls_properties[node_id]["freq"] = freq

    def get_properties(self):
        """Return traffic light properties.
        This is meant to be used by the generator to import traffic light data
        to the .net.xml file
        """
        return self.__tls_properties

    def actuated_default(self):
        """Return the default values for an actuated network.
        An actuated network is a network for a system where
        all junctions are actuated traffic lights.
        Returns
        -------
        tl_logic : dict
            traffic light logic
        """
        tl_type = "actuated"
        program_id = 1
        max_gap = 3.0
        detector_gap = 0.8
        show_detectors = True
        phases = [{
            "duration": "31",
            "minDur": "8",
            "maxDur": "45",
            "state": "GrGr"
        }, {
            "duration": "6",
            "minDur": "3",
            "maxDur": "6",
            "state": "yryr"
        }, {
            "duration": "31",
            "minDur": "8",
            "maxDur": "45",
            "state": "rGrG"
        }, {
            "duration": "6",
            "minDur": "3",
            "maxDur": "6",
            "state": "ryry"
        }]

        return {
            "tl_type": str(tl_type),
            "program_id": str(program_id),
            "max_gap": str(max_gap),
            "detector_gap": str(detector_gap),
            "show_detectors": show_detectors,
            "phases": phases
        }


class InFlows:
    """Used to add inflows to a network.
    Inflows can be specified for any edge that has a specified route or routes.
    """

    def __init__(self):
        """Instantiate Inflows."""
        self.__flows = []

    def add(self,
            edge,
            veh_type,
            vehs_per_hour=None,
            probability=None,
            period=None,
            depart_lane="first",
            depart_speed=0,
            name="flow",
            begin=1,
            end=86400,
            number=None,
            **kwargs):
        r"""Specify a new inflow for a given type of vehicles and edge.
        Parameters
        ----------
        edge : str
            starting edge for the vehicles in this inflow
        veh_type : str
            type of the vehicles entering the edge. Must match one of the types
            set in the Vehicles class
        vehs_per_hour : float, optional
            number of vehicles per hour, equally spaced (in vehicles/hour).
            Cannot be specified together with probability or period
        probability : float, optional
            probability for emitting a vehicle each second (between 0 and 1).
            Cannot be specified together with vehs_per_hour or period
        period : float, optional
            insert equally spaced vehicles at that period (in seconds). Cannot
            be specified together with vehs_per_hour or probability
        depart_lane : int or str
            the lane on which the vehicle shall be inserted. Can be either one
            of:
            * int >= 0: index of the lane (starting with rightmost = 0)
            * "random": a random lane is chosen, but the vehicle insertion is
              not retried if it could not be inserted
            * "free": the most free (least occupied) lane is chosen
            * "best": the "free" lane (see above) among those who allow the
              vehicle the longest ride without the need to change lane
            * "first": the rightmost lane the vehicle may use
            Defaults to "first".
        depart_speed : float or str
            the speed with which the vehicle shall enter the network (in m/s)
            can be either one of:
            - float >= 0: the vehicle is tried to be inserted using the given
              speed; if that speed is unsafe, departure is delayed
            - "random": vehicles enter the edge with a random speed between 0
              and the speed limit on the edge; the entering speed may be
              adapted to ensure a safe distance to the leading vehicle is kept
            - "speedLimit": vehicles enter the edge with the maximum speed that
              is allowed on this edge; if that speed is unsafe, departure is
              delayed
            Defaults to 0.
        name : str, optional
            prefix for the id of the vehicles entering via this inflow.
            Defaults to "flow"
        begin : float, optional
            first vehicle departure time (in seconds, minimum 1 second).
            Defaults to 1 second
        end : float, optional
            end of departure interval (in seconds). This parameter is not taken
            into account if 'number' is specified. Defaults to 24 hours
        number : int, optional
            total number of vehicles the inflow should create (due to rounding
            up, this parameter may not be exactly enforced and shouldn't be set
            too small). Default: infinite (c.f. 'end' parameter)
        kwargs : dict, optional
            see Note
        Note
        ----
        For information on the parameters start, end, vehs_per_hour,
        probability, period, number, as well as other vehicle type and routing
        parameters that may be added via \*\*kwargs, refer to:
        http://sumo.dlr.de/wiki/Definition_of_Vehicles,_Vehicle_Types,_and_Routes
        """
        # check for deprecations
        def deprecate(old, new):
            deprecated_attribute(self, old, new)
            new_val = kwargs[old]
            del kwargs[old]
            return new_val

        if "vehsPerHour" in kwargs:
            vehs_per_hour = deprecate("vehsPerHour", "vehs_per_hour")
        if "departLane" in kwargs:
            depart_lane = deprecate("departLane", "depart_lane")
        if "departSpeed" in kwargs:
            depart_speed = deprecate("departSpeed", "depart_speed")

        new_inflow = {
            "name": "%s_%d" % (name, len(self.__flows)),
            "vtype": veh_type,
            "edge": edge,
            "departLane": depart_lane,
            "departSpeed": depart_speed,
            "begin": begin,
            "end": end
        }
        new_inflow.update(kwargs)

        inflow_params = [vehs_per_hour, probability, period]
        n_inflow_params = len(inflow_params) - inflow_params.count(None)
        if n_inflow_params != 1:
            raise ValueError(
                "Exactly one among the three parameters 'vehs_per_hour', "
                "'probability' and 'period' must be specified in InFlows.add. "
                "{} were specified.".format(n_inflow_params))
        if probability is not None and (probability < 0 or probability > 1):
            raise ValueError(
                "Inflow.add called with parameter 'probability' set to {}, but"
                " probability should be between 0 and 1.".format(probability))
        if begin is not None and begin < 1:
            raise ValueError(
                "Inflow.add called with parameter 'begin' set to {}, but begin"
                " should be greater or equal than 1 second.".format(begin))

        if number is not None:
            del new_inflow["end"]
            new_inflow["number"] = number

        if vehs_per_hour is not None:
            new_inflow["vehsPerHour"] = vehs_per_hour
        if probability is not None:
            new_inflow["probability"] = probability
        if period is not None:
            new_inflow["period"] = period

        self.__flows.append(new_inflow)

    def get(self):
        """Return the inflows of each edge."""
        return self.__flows


def generate_net(data,
                 gui,
                 model,
                 nodes,
                 edges,
                 connections,
                 inflows,
                 veh_types,
                 traffic_lights,
                 save_flg=False):
    """Generate a network in the Aimsun template.

    Parameters
    ----------
    data : dict
        Data used to initilaized the Aimsun run
    gui : obj
        Aimsun graphic interface
    model : obj
        current Aimsun model
    nodes : list of dict
        all available nodes
    edges : list of dict
        all available edges
    connections : list of dict
        all available connections
    inflows : flow.core.params.InFlows
        the flow inflow object
    veh_types : list of dict
        list of vehicle types and their corresponding properties
    traffic_lights : flow.core.params.TrafficLightParams
        traffic light specific parameters
    """
    inflows = inflows.get()
    lane_width = 3.6  # TODO additional params??
    type_section = model.getType("GKSection")
    type_node = model.getType("GKNode")
    type_turn = model.getType("GKTurning")
    type_traffic_state = model.getType("GKTrafficState")
    type_vehicle = model.getType("GKVehicle")
    type_demand = model.getType("GKTrafficDemand")

    # draw edges
    for edge in edges:
        points = GKPoints()
        if "shape" in edge:
            for p in edge["shape"]:  # TODO add x, y offset (radius)
                new_point = GKPoint()
                new_point.set(p[0], p[1], 0)
                points.append(new_point)

            cmd = model.createNewCmd(model.getType("GKSection"))
            cmd.setPoints(edge["numLanes"], lane_width, points)
            model.getCommander().addCommand(cmd)
            section = cmd.createdObject()
            section.setName(edge["id"])
            edge_aimsun = model.getCatalog().findByName(
                edge["id"], type_section)
            edge_aimsun.setSpeed(edge["speed"] * 3.6)
        else:
            first_node, last_node = get_edge_nodes(edge, nodes)
            theta = get_edge_angle(first_node, last_node)
            first_node_offset = [0, 0]  # x, and y offset
            last_node_offset = [0, 0]  # x, and y offset

            # offset edge ends if there is a radius in the node
            if "radius" in first_node:
                first_node_offset[0] = first_node["radius"] * \
                    math.cos(theta*math.pi/180)
                first_node_offset[1] = first_node["radius"] * \
                    math.sin(theta*math.pi/180)
            if "radius" in last_node:
                last_node_offset[0] = - last_node["radius"] * \
                    math.cos(theta*math.pi/180)
                last_node_offset[1] = - last_node["radius"] * \
                    math.sin(theta*math.pi/180)

            # offset edge ends if there are multiple edges between nodes
            # find the edges that share the first node
            edges_shared_node = [edg for edg in edges
                                 if first_node["id"] == edg["to"] or
                                 last_node["id"] == edg["from"]]
            for new_edge in edges_shared_node:
                new_first_node, new_last_node = get_edge_nodes(new_edge, nodes)
                new_theta = get_edge_angle(new_first_node, new_last_node)
                if new_theta == theta - 180 or new_theta == theta + 180:
                    first_node_offset[0] += lane_width * 0.5 *\
                        math.sin(theta * math.pi / 180)
                    first_node_offset[1] -= lane_width * 0.5 * \
                        math.cos(theta * math.pi / 180)
                    last_node_offset[0] += lane_width * 0.5 *\
                        math.sin(theta * math.pi / 180)
                    last_node_offset[1] -= lane_width * 0.5 *\
                        math.cos(theta * math.pi / 180)
                    break

            new_point = GKPoint()
            new_point.set(first_node['x'] + first_node_offset[0],
                          first_node['y'] + first_node_offset[1],
                          0)
            points.append(new_point)
            new_point = GKPoint()
            new_point.set(last_node['x'] + last_node_offset[0],
                          last_node['y'] + last_node_offset[1],
                          0)
            points.append(new_point)
            cmd = model.createNewCmd(type_section)
            cmd.setPoints(edge["numLanes"], lane_width, points)
            model.getCommander().addCommand(cmd)
            section = cmd.createdObject()
            section.setName(edge["id"])
            edge_aimsun = model.getCatalog().findByName(
                edge["id"], type_section)
            edge_aimsun.setSpeed(edge["speed"] * 3.6)

    # draw nodes and connections
    for node in nodes:
        # add a new node in Aimsun
        node_pos = GKPoint()
        node_pos.set(node['x'], node['y'], 0)
        cmd = model.createNewCmd(type_node)
        cmd.setPosition(node_pos)
        model.getCommander().addCommand(cmd)
        new_node = cmd.createdObject()
        new_node.setName(node["id"])

        # list of edges from and to the node
        from_edges = [
            edge['id'] for edge in edges if edge['from'] == node['id']]
        to_edges = [edge['id'] for edge in edges if edge['to'] == node['id']]

        # if the node is a junction with a list of connections
        if len(to_edges) > 1 and len(from_edges) > 1 \
                and connections[node['id']] is not None:
            # add connections
            for connection in connections[node['id']]:
                cmd = model.createNewCmd(type_turn)
                from_section = model.getCatalog().findByName(
                    connection["from"], type_section, True)
                to_section = model.getCatalog().findByName(
                    connection["to"], type_section, True)
                cmd.setTurning(from_section, to_section)
                model.getCommander().addCommand(cmd)
                turn = cmd.createdObject()
                turn_name = "{}_to_{}".format(connection["from"],
                                              connection["to"])
                turn.setName(turn_name)
                existing_node = turn.getNode()
                if existing_node is not None:
                    existing_node.removeTurning(turn)
                # add the turning to the node
                new_node.addTurning(turn, False, True)

        # if the node is not a junction or connections is None
        else:
            for i in range(len(from_edges)):
                for j in range(len(to_edges)):
                    cmd = model.createNewCmd(type_turn)
                    to_section = model.getCatalog().findByName(
                        from_edges[i], type_section, True)
                    from_section = model.getCatalog().findByName(
                        to_edges[j], type_section, True)
                    cmd.setTurning(from_section, to_section)
                    model.getCommander().addCommand(cmd)
                    turn = cmd.createdObject()
                    turn_name = "{}_to_{}".format(from_edges[i], to_edges[j])
                    turn.setName(turn_name)
                    existing_node = turn.getNode()
                    if existing_node is not None:
                        existing_node.removeTurning(turn)

                    # add the turning to the node
                    new_node.addTurning(turn, False, True)

    # get the control plan
    control_plan = model.getCatalog().findByName(
            "Control Plan", model.getType("GKControlPlan"))

    # add traffic lights
    tls_properties = traffic_lights.get_properties()
    # determine junctions
    junctions = get_junctions(nodes)
    # add meters for all nodes in junctions
    for node in junctions:
        phases = tls_properties[node['id']]["phases"]
        print(phases)
        create_node_meters(model, control_plan, node['id'], phases)

    # set vehicle types
    vehicles = model.getCatalog().getObjectsByType(type_vehicle)
    if vehicles is not None:
         print("Type Vehicle: %s" % (vehicles))
    if vehicles is not None:
        all_names = []
        for ids in vehicles.keys():
            all_names.append(vehicles[ids].getName())
        print("vehicles names %r " % (all_names))
        for ids in vehicles.keys():
            vehicle = vehicles[ids]
            name = vehicle.getName()
            if name == "Car":
                for veh_type in veh_types:
                    cmd = GKObjectDuplicateCmd()
                    cmd.init(vehicle)
                    model.getCommander().addCommand(cmd)
                    new_veh = cmd.createdObject()
                    new_veh.setName(veh_type["veh_id"])

    # Create new states based on vehicle types
    for veh_type in veh_types:
        new_state = create_state(model, veh_type["veh_id"])
        # find vehicle type
        veh_type = model.getCatalog().findByName(
            veh_type["veh_id"], model.getType("GKVehicle"))
        # set state vehicles
        new_state.setVehicle(veh_type)

    # add traffic inflows to traffic states
    for inflow in inflows:
        traffic_state_aimsun = model.getCatalog().findByName(
            inflow["vtype"], type_traffic_state)
        edge_aimsun = model.getCatalog().findByName(
            inflow['edge'], type_section)
        traffic_state_aimsun.setEntranceFlow(
            edge_aimsun, None, inflow.get('vehsPerHour', 0))

    # get traffic demand
    demand = model.getCatalog().findByName(
        "Traffic Demand 864", type_demand)
    # clear the demand of any previous item
    demand.removeSchedule()

    # set traffic demand
    for veh_type in veh_types:
        # find the state for each vehicle type
        state_car = model.getCatalog().findByName(
            veh_type["veh_id"], type_traffic_state)
        if demand is not None and demand.isA("GKTrafficDemand"):
            # Add the state
            if state_car is not None and state_car.isA("GKTrafficState"):
                set_demand_item(model, demand, state_car)
            model.getCommander().addCommand(None)
        else:
            create_traffic_demand(model, veh_type["veh_id"])  # TODO debug

    # set the view to "whole world" in Aimsun
    view = None if gui is None else gui.getActiveViewWindow().getView()
    if view is not None:
        view.wholeWorld()

    # set view mode, each vehicle type with different color
    set_vehicles_color(model)

    # set API
    network_name = data.get("network_name", "")
    scenario = model.getCatalog().findByName(
        network_name, model.getType("GKScenario"))  # find scenario
    scenario_data = scenario.getInputData()
    scenario_data.addExtension(
        os.path.join(PROJECT_PATH, "flow/utils/aimsun/test_run.py"), True
    )

    # save
    if save_flg:
        if gui is not None:
            gui.save(model, 'flow.ang', GGui.GGuiSaveType.eSaveAs)



def generate_net_osm(data, gui, model, file_name, inflows, veh_types, save_flg=False):
    """Generate a network from an osm file.

    Parameters
    ----------
    data : dict
        Data used to initilaized the Aimsun run
    gui : obj
        Aimsun graphic interface
    model : obj
        current Aimsun model
    file_name : str
        path to the osm file
    inflows : flow.core.params.InFlows
        the flow inflow object
    veh_types : list of dict
        list of vehicle types and their corresponding properties
    """
    inflows = inflows.get()

    type_section = model.getType("GKSection")
    type_traffic_state = model.getType("GKTrafficState")
    type_vehicle = model.getType("GKVehicle")
    type_demand = model.getType("GKTrafficDemand")

    # load OSM file
    layer = None
    point = GKPoint()
    point.set(0, 0, 0)
    box = GKBBox()
    box.set(-1000, -1000, 0, 1000, 1000, 0)

    model.importFile(file_name, layer, point, box)

    # set vehicle types
    vehicles = model.getCatalog().getObjectsByType(type_vehicle)
    if vehicles is not None:
        for ids in vehicles.keys():
            vehicle = vehicles[ids]
            name = vehicle.getName()
            if name == "Car":
                for veh_type in veh_types:
                    cmd = GKObjectDuplicateCmd()
                    cmd.init(vehicle)
                    model.getCommander().addCommand(cmd)
                    new_veh = cmd.createdObject()
                    new_veh.setName(veh_type["veh_id"])

    # Create new states based on vehicle types
    for veh_type in veh_types:
        new_state = create_state(model, veh_type["veh_id"])
        # find vehicle type
        veh_type = model.getCatalog().findByName(
            veh_type["veh_id"], model.getType("GKVehicle"))
        # set state vehicles
        new_state.setVehicle(veh_type)

    # add traffic inflows to traffic states
    if inflows is not None:
        for inflow in inflows:
            traffic_state_aimsun = model.getCatalog().findByName(
                inflow["vtype"], type_traffic_state)
            edge_aimsun = model.getCatalog().findByName(
                inflow['edge'], type_section)
            traffic_state_aimsun.setEntranceFlow(
                edge_aimsun, None, inflow.get('vehsPerHour', 0))

    # get traffic demand
    demand = model.getCatalog().findByName(
        "Traffic Demand 864", type_demand)
    # clear the demand of any previous item
    demand.removeSchedule()

    # set traffic demand
    for veh_type in veh_types:
        # find the state for each vehicle type
        state_car = model.getCatalog().findByName(
            veh_type["veh_id"], type_traffic_state)
        if demand is not None and demand.isA("GKTrafficDemand"):
            # Add the state
            if state_car is not None and state_car.isA("GKTrafficState"):
                set_demand_item(model, demand, state_car)
            model.getCommander().addCommand(None)
        else:
            create_traffic_demand(model, veh_type["veh_id"])  # TODO debug

    # set the view to "whole world" in Aimsun
    view = None if gui is None else gui.getActiveViewWindow().getView()
    if view is not None:
        view.wholeWorld()

    # set view mode, each vehicle type with different color
    set_vehicles_color(model)

    # set API
    network_name = data.get("network_name", "")
    scenario = model.getCatalog().findByName(
        network_name, model.getType("GKScenario"))  # find scenario
    scenario_data = scenario.getInputData()
    scenario_data.addExtension(
        os.path.join(PROJECT_PATH, "flow/utils/aimsun/test_run.py"), True
    )

    # save
    if save_flg:
        if gui is not None:
            gui.save(model, 'flow.ang', GGui.GGuiSaveType.eSaveAs)


def get_junctions(nodes):
    """Return the nodes with traffic lights.

    Parameters
    ----------
    nodes : list of dict
        all available nodes

    Returns
    -------
    list of dict
        the nodes with traffic lights
    """
    junctions = []  # TODO check
    for node in nodes:
        if "type" in node:
            if node["type"] == "traffic_light":
                junctions.append(node)
    return junctions


def get_edge_nodes(edge, nodes):
    """Get first and last nodes of an edge.

    Parameters
    ----------
    edge : dict
        the edge information
    nodes : list of dict
        all available nodes

    Returns
    -------
    dict
        information on the first node
    dict
        information on the last node
    """
    first_node = next(node for node in nodes
                      if node["id"] == edge["from"])
    last_node = next(node for node in nodes
                     if node["id"] == edge["to"])
    return first_node, last_node


def get_edge_angle(first_node, last_node):
    """Compute the edge angle.

    Parameters
    ----------
    first_node : dict
        information on the first node
    last_node : dict
        information on the last node

    Returns
    -------
    float
        edge angle
    """
    del_x = last_node['x'] - first_node['x']
    del_y = last_node['y'] - first_node['y']
    theta = math.atan2(del_y, del_x) * 180 / math.pi
    return theta


def get_state_folder(model):
    """Return traffic state folder.

    If the folder doesn't exist, a new folder will be created.

    Parameters
    ----------
    model : GKModel
        Aimsun model object

    Returns
    -------
    GKFolder
        an Aimsun folder object which contains traffic state.
    """
    folder_name = "GKModel::trafficStates"
    folder = model.getCreateRootFolder().findFolder(folder_name)
    if folder is None:
        folder = GKSystem.getSystem().createFolder(
            model.getCreateRootFolder(), folder_name)
    return folder


def create_state(model, name):
    """Create a traffic state object.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    name : str
        name of the traffic state

    Returns
    -------
    GKTrafficState
        an Aimsun traffic state object
    """
    state = GKSystem.getSystem().newObject("GKTrafficState", model)
    state.setName(name)
    folder = get_state_folder(model)
    folder.append(state)
    return state


def get_demand_folder(model):
    """Return traffic demand folder.

    If the folder doesn't exist, a new folder will be created.

    Parameters
    ----------
    model : GKModel
        Aimsun model object

    Returns
    -------
    GKFolder
        an Aimsun folder object which contains traffic demand.
    """
    folder_name = "GKModel::trafficDemands"
    folder = model.getCreateRootFolder().findFolder(folder_name)
    if folder is None:
        folder = GKSystem.getSystem().createFolder(
            model.getCreateRootFolder(), folder_name)
    return folder


def create_traffic_demand(model, name):
    """Create a traffic demand object.

    If the folder doesn't exist, a new folder will be created.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    name : str
        name of the traffic state

    Returns
    -------
    GKTrafficDemand
        an Aimsun traffic demand object
    """
    demand = GKSystem.getSystem().newObject("GKTrafficDemand", model)
    demand.setName(name)
    folder = get_demand_folder(model)
    folder.append(demand)
    return demand


def set_demand_item(model, demand, item):
    """Set a traffic demand item.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    demand : GKTrafficDemand
        an Aimsun traffic demand object
    item : GKTrafficDemandItem
        a traffic item which is valid for a vehicle type and a time interval
    """
    if item.getVehicle() is None:
        model.getLog().addError("Invalid Demand Item: no vehicle")
    else:
        schedule = GKScheduleDemandItem()
        schedule.setTrafficDemandItem(item)
        # Starts at 8:00:00 AM
        schedule.setFrom(8 * 3600)
        # Duration: 500 hour
        schedule.setDuration(500 * 3600)
        demand.addToSchedule(schedule)


def set_state_vehicle(model, state, veh_type_name):
    """Set state vehicle type.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    state : GKTrafficState
        an Aimsun traffic state object
    veh_type_name : str
        name of the vehicle type
    """
    # find vehicle type
    veh_type = model.getCatalog().findByName(
        veh_type_name, model.getType("GKVehicle"))
    # set state vehicles
    state.setVehicle(veh_type)


def set_vehicles_color(model):
    """Set view mode and view style.

    View mode and view style are used to show different vehicle types with
    different colors. View mode and view style are named
    "DYNAMIC: Simulation Vehicles by Vehicle Type".

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    """
    view_mode = model.getGeoModel().findMode(
        "GKViewMode::VehiclesByVehicleType", False)
    if view_mode is None:
        view_mode = GKSystem.getSystem().newObject("GKViewMode", model)
        view_mode.setInternalName("GKViewMode::VehiclesByVehicleType")
        view_mode.setName("DYNAMIC: Simulation Vehicles by Vehicle Type")
        model.getGeoModel().addMode(view_mode)
    view_mode.removeAllStyles()
    view_style = model.getGeoModel().findStyle(
        "GKViewModeStyle::VehiclesByVehicleType")
    if view_style is None:
        view_style = GKSystem.getSystem().newObject("GKViewModeStyle", model)
        view_style.setInternalName("GKViewModeStyle::VehiclesByVehicleType")
        view_style.setName("DYNAMIC: Simulation Vehicles by Vehicle Type")
        view_style.setStyleType(GKViewModeStyle.eColor)
        view_style.setVariableType(GKViewModeStyle.eDiscrete)
        sim_type = model.getType("GKSimVehicle")
        type_col = sim_type.getColumn("GKSimVehicle::vehicleTypeAtt",
                                      GKType.eSearchOnlyThisType)
        view_style.setColumn(sim_type, type_col)
        ramp = GKColorRamp()
        ramp.setType(GKColorRamp.eRGB)
        vehicles = model.getCatalog().getObjectsByType(
            model.getType("GKVehicle"))
        if vehicles is not None:
            ramp.lines(len(vehicles))
            all_veh = [vehicles[ids] for ids in vehicles.keys()]
            for i, vehicle in enumerate(all_veh):
                color_range = view_style.addRange(vehicle.getName())
                color_range.color = ramp.getColor(i)
        model.getGeoModel().addStyle(view_style)
    view_mode.addStyle(view_style)


def get_control_plan_folder(model):
    """Return control plan folder.

    If the folder doesn't exist, a new folder will be created.

    Parameters
    ----------
    model : GKModel
        Aimsun model object

    Returns
    -------
    GKFolder
        an Aimsun folder object which contains control plan.
    """
    folder_name = "GKModel::controlPlans"
    folder = model.getCreateRootFolder().findFolder(folder_name)
    if folder is None:
        folder = GKSystem.getSystem().createFolder(model.getCreateRootFolder(),
                                                   folder_name)
    return folder


def create_control_plan(model, name):
    """Create a traffic control plan object.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    name : str
        name of the control plan

    Returns
    -------
    GKControlPlan
        an Aimsun control plan object
    """
    control_plan = GKSystem.getSystem().newObject("GKControlPlan", model)
    control_plan.setName(name)
    folder = get_control_plan_folder(model)
    folder.append(control_plan)
    return control_plan


def create_meter(model, edge):
    """Create a metering object.

    Parameters
    ----------
    model : GKModel
        Aimsun model object
    edge : str
        name of the edge

    Returns
    -------
    GKSectionObject
        an Aimsun metering (section object) object
    """
    section = model.getCatalog().findByName(edge, model.getType("GKSection"))
    meter_length = 2
    pos = section.length2D() - meter_length
    type = model.getType("GKMetering")
    cmd = model.createNewCmd(model.getType("GKSectionObject"))
    # TODO double check the zeros
    cmd.init(type, section, 0, 0, pos, meter_length)
    model.getCommander().addCommand(cmd)
    meter = cmd.createdObject()
    meter.setName("meter_{}".format(section.getName()))
    return meter


def set_metering_times(
        cp, meter, cycle, green, yellow, offset, min_green, max_green):
    """Set a meter timing plan.

    Parameters
    ----------
    cp : GKControlPlan
        an aimsun control plan object
    meter : GKSectionObject
        an Aimsun metering (section object) object
    cycle : int
        cycle length
    green : int
        green phase duration
    yellow : int
        yellow phase duration
    offset : int
        offset duration
    min_green : int
        minimum green phase duration
    max_green : int
        maximum green phase duration
    """
    cp_meter = cp.createControlMetering(meter)
    cp_meter.setControlMeteringType(GKControlMetering.eExternal)
    cp_meter.setCycle(cycle)
    cp_meter.setGreen(green)
    cp_meter.setYellowTime(yellow)
    cp_meter.setOffset(offset)
    cp_meter.setMinGreen(min_green)
    cp_meter.setMaxGreen(max_green)


def create_node_meters(model, cp, node_id, phases):
    """Create meters for a node.

    Parameters
    ----------
    model:
    cp : GKControlPlan
        an aimsun control plan object
    node_id : str
        node ID
    phases :  list  of dict
        list of phases to be followed by the traffic light

    Returns
    -------
    list of GKSectionObject
        list of meters in the node
    """
    meters = []
    signal_groups = {}
    for connection in connections[node_id]:
        if connection["signal_group"] in signal_groups:
            signal_groups[
                connection["signal_group"]].append(connection["from"])
        else:
            signal_groups[connection["signal_group"]] = [connection["from"]]

    # get cycle length
    cycle = 0
    for signal_group, edges in signal_groups.items():
        cycle += int(phases[signal_group]["duration"]) + \
                 int(phases[signal_group]["yellow"])

    # set a meter for each edge in each signal group cycle length
    sum_phases = 0
    for signal_group, edges in signal_groups.items():
        green = int(phases[signal_group]["duration"])
        yellow = int(phases[signal_group]["yellow"])
        min_green = int(phases[signal_group]["minDur"])
        max_green = int(phases[signal_group]["maxDur"])
        for edge in edges:
            meter = create_meter(model, edge)
            set_metering_times(cp, meter, cycle, green, yellow,
                               sum_phases, min_green, max_green)
            meters.append(meter)
        sum_phases += green + yellow
    return meters


def set_sim_step(model, experiment, sim_step):
    """Set the simulation step of an Aimsun experiment.

    Parameters
    ----------
    model : obj
        the Aimsun model
    experiment : GKTExperiment
        the experiment object
    sim_step : float
        desired simulation step
    """
    # Get Simulation Step attribute column
    col_sim = model.getColumn('GKExperiment::simStepAtt')
    # Set new simulation step value
    experiment.setDataValue(col_sim, sim_step)




def load_model_from_gui_or_console():
    isgui = True
    filepath = os.path.join(PROJECT_PATH, "flow/utils/aimsun/Aimsun_Flow.ang")
    if len(sys.argv) > 3 and sys.argv[3] == 'console':
        isgui = False
    gui = None
    console = None
    model = None
    if isgui:
        # Load an empty template
        gui = GKGUISystem.getGUISystem().getActiveGui()
        gui.newDoc(filepath, "EPSG:32601")
        model = gui.getActiveModel()
    else:
        console = ANGConsole()
        res = console.open(filepath )
        if not res:
            console.getLog().addError( "Cannot load the network" )
            print("cannot load network")
        else:
            model = console.getModel()
    return gui, console, model
    


# Load an empty template
gui, console, model = load_model_from_gui_or_console()

if len(sys.argv) > 1:
    # HACK: Store port in author
    port_string = sys.argv[1]
    model.setAuthor(port_string)
else:
    port_string = ""
    model.setAuthor("No Author")

save_flg = False

# collect the network-specific data
data_file = 'flow/core/kernel/network/data_%s.json'%port_string
print("Loading  File %s/%s " % (PROJECT_PATH, data_file))
filename = osp.join(PROJECT_PATH, data_file)
if osp.exists(filename):
    with open(filename) as f:
        data = json.load(f)
else:
    data = {}

# export the data from the dictionary
veh_types = data.get('vehicle_types', [])
osm_path = data.get('osm_path')

if data.get('inflows') is not None:
    inflows = InFlows()
    inflows.__dict__ = data['inflows'].copy()
else:
    inflows = None

if data.get('traffic_lights') is not None:
    traffic_lights = TrafficLightParams()
    traffic_lights.__dict__ = data['traffic_lights'].copy()
else:
    traffic_lights = None

print("Loading the data %s " % (osm_path is not None))

if osm_path is not None:
    generate_net_osm(data, gui, model, osm_path, inflows, veh_types, save_flg)
    edge_osm = {}

    section_type = model.getType("GKSection")
    for types in model.getCatalog().getUsedSubTypesFromType(section_type):
        for ids in types.keys():
            s = types[ids]
            s_id = s.getId()
            num_lanes = s.getNbFullLanes()
            length = s.length2D()
            speed = s.getSpeed()
            edge_osm[s_id] = {"speed": speed,
                              "length": length,
                              "numLanes": num_lanes}
    filename2 = osp.join(PROJECT_PATH, 'flow/utils/aimsun/osm_edges_%s.json' % port_string)
    with open(filename2, 'w') as outfile:
        json.dump(edge_osm, outfile, sort_keys=True, indent=4)

else:
    print("Loading the data from loaded json ")
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    types = data.get('types', [])
    connections = data.get('connections', None)

    for i in range(len(edges)):
        if 'type' in edges[i]:
            for typ in types:
                if typ['id'] == edges[i]['type']:
                    new_dict = deepcopy(typ)
                    new_dict.pop("id")
                    edges[i].update(new_dict)
                    break

    generate_net(data, gui, model, nodes, edges, connections, inflows, veh_types, traffic_lights, save_flg)

# set sim step
sim_step = data.get("sim_step", 0.1)
# retrieve experiment by name
experiment_name = data.get("experiment_name", "XPNoName")
experiment = model.getCatalog().findByName(
    experiment_name, model.getType("GKTExperiment")
)
set_sim_step(model, experiment, sim_step)

print("GENERATE RUN SIMULATION")

# run the simulation
# find the replication
replication_name = data.get("replication_name", "")
replication = model.getCatalog().findByName(replication_name)
# execute, "play": run with GUI, "execute": run in batch mode
mode = 'play' if gui is not None and data.get('render', False) is True else 'execute'
GKSystem.getSystem().executeAction(mode, replication, [], "")
print("GENERATE RUNNING SIMULATION")
