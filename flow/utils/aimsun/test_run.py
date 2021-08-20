# flake8: noqa
"""Script used to interact with Aimsun's API during the simulation phase."""
import sys
import os

# sys.path.append(os.path.join(config.AIMSUN_NEXT_PATH,
#                              'programming/Aimsun Next API/AAPIPython/Micro'))

AIMSUN_NEXT_PATH = os.environ.get("AIMSUN_NEXT_PATH", None)

print("TEST RUN API")
print("TEST RUN AIMSUN_NEXT_PATH: %s" % (AIMSUN_NEXT_PATH))

sys.path.append(
    os.path.join(
        AIMSUN_NEXT_PATH,
        'programming/Aimsun Next API/python/private/Micro'
    )
)

import AAPI as aimsun_api
from AAPI import *
from PyANGKernel import *
import socket
import struct
from _thread import start_new_thread

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__
    

constants = {
    ###############################################################################
    #                             Simulation Commands                             #
    ###############################################################################

    #: simulation step
    'SIMULATION_STEP': 0x00,

    #: terminate the simulation
    'SIMULATION_TERMINATE': 0x01,


    ###############################################################################
    #                               Network Commands                              #
    ###############################################################################

    #: get the edge name in aimsun
    'GET_EDGE_NAME': 0x02,


    ###############################################################################
    #                               Vehicle Commands                              #
    ###############################################################################

    #: add a vehicle
    'ADD_VEHICLE': 0x03,

    #: remove a vehicle
    'REMOVE_VEHICLE': 0x04,

    #: set vehicle speed
    'VEH_SET_SPEED': 0x05,

    #: apply vehicle lane change
    'VEH_SET_LANE': 0x06,

    #: set vehicle route
    'VEH_SET_ROUTE': 0x07,

    #: set color
    'VEH_SET_COLOR': 0x08,

    #: get IDs of entering vehicles
    'VEH_GET_ENTERED_IDS': 0x09,

    #: get IDs of exiting vehicles
    'VEH_GET_EXITED_IDS': 0x0A,

    #: get vehicle type in Aimsun
    'VEH_GET_TYPE_ID': 0x0B,

    #: get vehicle static information
    'VEH_GET_STATIC': 0x0C,

    #: get vehicle tracking information
    'VEH_GET_TRACKING': 0x0D,

    #: get vehicle leader
    'VEH_GET_LEADER': 0x0E,

    #: get vehicle follower
    'VEH_GET_FOLLOWER': 0x0F,

    #: get vehicle next section
    'VEH_GET_NEXT_SECTION': 0x10,

    #: get vehicle route
    'VEH_GET_ROUTE': 0x11,

    #: get vehicle speed if no API command was submitted
    'VEH_GET_DEFAULT_SPEED': 0x12,

    #: get vehicle angle
    'VEH_GET_ORIENTATION': 0x13,

    # TODO: not 100% sure what this is...
    'VEH_GET_TIMESTEP': 0x14,

    # TODO: not 100% sure what this is...
    'VEH_GET_TIMEDELTA': 0x15,

    #: get vehicle type name in Aimsun
    'VEH_GET_TYPE_NAME': 0x16,

    #: get vehicle length
    'VEH_GET_LENGTH': 0x17,

    #: set vehicle as tracked in Aimsun
    'VEH_SET_TRACKED': 0x18,

    #: set vehicle as untracked in Aimsun
    'VEH_SET_NO_TRACKED': 0x19,


    ###############################################################################
    #                           Traffic Light Commands                            #
    ###############################################################################

    #: get traffic light IDs
    'TL_GET_IDS': 0x1A,

    #: set traffic light state
    'TL_SET_STATE': 0x1B,

    #: get traffic light state
    'TL_GET_STATE': 0x1C,
}

ac = dotdict(constants)
model = GKSystem.getSystem().getActiveModel()
PORT = int(model.getAuthor())
entered_vehicles = []
exited_vehicles = []


def send_message(conn, in_format, values):
    """Send a message to the client.

    If the message is a string, it is sent in segments of length 256 (if the
    string is longer than such) and concatenated on the client end.

    Parameters
    ----------
    conn : socket.socket
        socket for server connection
    in_format : str
        format of the input structure
    values : tuple of Any
        commands to be encoded and issued to the client
    """
    if in_format == 'str':
        packer = struct.Struct(format='i')
        values = values[0]
        
        if isinstance(values, str):
            values = values.encode()

        # when the message is too large, send value in segments and inform the
        # client that additional information will be sent. The value will be
        # concatenated on the other end
        while len(values) > 256:
            # send the next set of data
            conn.send(values[:256])
            values = values[256:]

            # wait for a reply
            data = None
            while data is None:
                data = conn.recv(2048)

            # send a not-done signal
            packed_data = packer.pack(*(1,))
            conn.send(packed_data)

        # send the remaining components of the message (which is of length less
        # than or equal to 256)
        conn.send(values)

        # wait for a reply
        data = None
        while data is None:
            data = conn.recv(2048)

        # send a done signal
        packed_data = packer.pack(*(0,))
        conn.send(packed_data)
    else:
        packer = struct.Struct(format=in_format)
        packed_data = packer.pack(*values)
        conn.send(packed_data)


def retrieve_message(conn, out_format):
    """Retrieve a message from the client.

    Parameters
    ----------
    conn : socket.socket
        socket for server connection
    out_format : str or None
        format of the output structure

    Returns
    -------
    Any
        received message
    """
    unpacker = struct.Struct(format=out_format)
    try:
        data = conn.recv(unpacker.size)
        unpacked_data = unpacker.unpack(data)
    finally:
        pass
    return unpacked_data


def threaded_client(conn):
    """Create a threaded process.

    This process is called every simulation step to interact with the aimsun
    server, and terminates once the simulation is ready to execute a new step.

    Parameters
    ----------
    conn : socket.socket
        socket for server connection
    """
    # send feedback that the connection is active
    conn.send(b'Ready.')

    done = False
    while not done:
        # receive the next message
        data = conn.recv(2048)

        if data is not None:
            # if the message is empty, search for the next message
            if data == '':
                continue

            # convert to integer
            data = int(data)

            # if the simulation step is over, terminate the ring and let
            # the step be executed
            if data == ac.SIMULATION_STEP:
                send_message(conn, in_format='i', values=(0,))
                done = True

            # Note that alongside this, the process is closed in Flow,
            # thereby terminating the socket connection as well.
            elif data == ac.SIMULATION_TERMINATE:
                send_message(conn, in_format='i', values=(0,))
                done = True

            elif data == ac.ADD_VEHICLE:
                send_message(conn, in_format='i', values=(0,))

                edge, lane, type_id, pos, speed, next_section = \
                    retrieve_message(conn, 'i i i f f i')

                # 1 if tracked, 0 otherwise
                tracking = 1

                veh_id = aimsun_api.AKIPutVehTrafficFlow(
                    edge, lane+1, type_id, pos, speed, next_section,
                    tracking
                )

                send_message(conn, in_format='i', values=(veh_id,))

            elif data == ac.REMOVE_VEHICLE:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')
                aimsun_api.AKIVehTrackedRemove(veh_id)
                send_message(conn, in_format='i', values=(0,))

            elif data == ac.VEH_SET_SPEED:
                send_message(conn, in_format='i', values=(0,))
                veh_id, speed = retrieve_message(conn, 'i f')
                new_speed = speed * 3.6
                # aimsun_api.AKIVehTrackedForceSpeed(veh_id, new_speed)
                aimsun_api.AKIVehTrackedModifySpeed(veh_id, new_speed)
                send_message(conn, in_format='i', values=(0,))

            elif data == ac.VEH_SET_LANE:
                conn.send(b'Set vehicle lane.')
                veh_id, target_lane = retrieve_message(conn, 'i i')
                aimsun_api.AKIVehTrackedModifyLane(veh_id, target_lane)
                send_message(conn, in_format='i', values=(0,))

            elif data == ac.VEH_SET_ROUTE:
                send_message(conn, in_format='i', values=(0,))
                # TODO

            elif data == ac.VEH_SET_COLOR:
                send_message(conn, in_format='i', values=(0,))
                veh_id, r, g, b = retrieve_message(conn, 'i i i i')
                # TODO
                send_message(conn, in_format='i', values=(0,))

            elif data == ac.VEH_SET_TRACKED:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')
                aimsun_api.AKIVehSetAsTracked(veh_id)

            elif data == ac.VEH_SET_NO_TRACKED:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')
                aimsun_api.AKIVehSetAsNoTracked(veh_id)

            elif data == ac.VEH_GET_ENTERED_IDS:
                send_message(conn, in_format='i', values=(0,))

                data = None
                while data is None:
                    data = conn.recv(256)

                global entered_vehicles
                if len(entered_vehicles) == 0:
                    output = '-1'
                else:
                    output = ':'.join([str(e) for e in entered_vehicles])
                send_message(conn, in_format='str', values=(output,))
                entered_vehicles = []

            elif data == ac.VEH_GET_EXITED_IDS:
                send_message(conn, in_format='i', values=(0,))

                data = None
                while data is None:
                    data = conn.recv(256)

                global exited_vehicles
                if len(exited_vehicles) == 0:
                    output = '-1'
                else:
                    output = ':'.join([str(e) for e in exited_vehicles])
                send_message(conn, in_format='str', values=(output,))
                exited_vehicles = []

            elif data == ac.VEH_GET_TYPE_ID:
                send_message(conn, in_format='i', values=(0,))

                # get the type ID in flow
                type_id = None
                while type_id is None:
                    type_id = conn.recv(2048)
                    
                if isinstance(type_id, bytes):
                    type_id = type_id.decode()

                # convert the edge name to an edge name in Aimsun
                model = GKSystem.getSystem().getActiveModel()
                type_vehicle = model.getType("GKVehicle")
                vehicle = model.getCatalog().findByName(
                    type_id, type_vehicle)
                aimsun_type = vehicle.getId()
                aimsun_type_pos = AKIVehGetVehTypeInternalPosition(aimsun_type)

                send_message(conn, in_format='i', values=(aimsun_type_pos,))

            # FIXME can probably be done more efficiently cf. VEH_GET_TYPE_ID
            elif data == ac.VEH_GET_TYPE_NAME:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')

                static_info = aimsun_api.AKIVehGetStaticInf(veh_id)
                typename = aimsun_api.AKIVehGetVehTypeName(static_info.type)

                anyNonAsciiChar = aimsun_api.boolp()
                output = str(aimsun_api.AKIConvertToAsciiString(
                    typename, True, anyNonAsciiChar))

                send_message(conn, in_format='str', values=(output,))

            elif data == ac.VEH_GET_LENGTH:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')

                static_info = aimsun_api.AKIVehGetStaticInf(veh_id)
                output = static_info.length

                send_message(conn, in_format='f', values=(output,))

            elif data == ac.VEH_GET_STATIC:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')

                static_info = aimsun_api.AKIVehGetStaticInf(veh_id)
                output = (static_info.report,
                          static_info.idVeh,
                          static_info.type,
                          static_info.length,
                          static_info.width,
                          static_info.maxDesiredSpeed,
                          static_info.maxAcceleration,
                          static_info.normalDeceleration,
                          static_info.maxDeceleration,
                          static_info.speedAcceptance,
                          static_info.minDistanceVeh,
                          static_info.giveWayTime,
                          static_info.guidanceAcceptance,
                          static_info.enrouted,
                          static_info.equipped,
                          static_info.tracked,
                          static_info.keepfastLane,
                          static_info.headwayMin,
                          static_info.sensitivityFactor,
                          static_info.reactionTime,
                          static_info.reactionTimeAtStop,
                          static_info.reactionTimeAtTrafficLight,
                          static_info.centroidOrigin,
                          static_info.centroidDest,
                          static_info.idsectionExit,
                          static_info.idLine)

                send_message(conn,
                             in_format='i i i f f f f f f f f f f i i i ? '
                                       'f f f f f i i i i',
                             values=output)

            elif data == ac.VEH_GET_TRACKING:
                send_message(conn, in_format='i', values=(0,))

                info_bitmap = None
                while info_bitmap is None:
                    info_bitmap = conn.recv(2048)

                # bitmap is built as follows:
                #   21 bits representing what information is to be returned
                #   a ':' character
                #   the id of the vehicle
                #   a bit representing whether or not the vehicle is tracked

                # retrieve the tracked boolean
                tracked = info_bitmap[-1]
                info_bitmap = info_bitmap[:-1]

                # separate the actual bitmap from the vehicle id
                s = ""
                if isinstance(info_bitmap, bytes):
                    info_bitmap = info_bitmap.decode()
                for i in range(len(info_bitmap)):
                    if info_bitmap[i] == ':':
                        info_bitmap = info_bitmap[i+1:]
                        break
                    s += info_bitmap[i]
                veh_id = int(s)

                # retrieve the tracking info of the vehicle
                if tracked == '1':
                    tracking_info = aimsun_api.AKIVehTrackedGetInf(veh_id)
                else:
                    tracking_info = aimsun_api.AKIVehGetInf(veh_id)

                data = (
                          # tracking_info.report,
                          # tracking_info.idVeh,
                          # tracking_info.type,
                          tracking_info.CurrentPos,
                          tracking_info.distance2End,
                          tracking_info.xCurrentPos,
                          tracking_info.yCurrentPos,
                          tracking_info.zCurrentPos,
                          tracking_info.xCurrentPosBack,
                          tracking_info.yCurrentPosBack,
                          tracking_info.zCurrentPosBack,
                          tracking_info.CurrentSpeed,
                          # tracking_info.PreviousSpeed,
                          tracking_info.TotalDistance,
                          # tracking_info.SystemGenerationT,
                          # tracking_info.SystemEntranceT,
                          tracking_info.SectionEntranceT,
                          tracking_info.CurrentStopTime,
                          tracking_info.stopped,
                          tracking_info.idSection,
                          tracking_info.segment,
                          tracking_info.numberLane,
                          tracking_info.idJunction,
                          tracking_info.idSectionFrom,
                          tracking_info.idLaneFrom,
                          tracking_info.idSectionTo,
                          tracking_info.idLaneTo)
                
                # form the output and output format according to the bitmap
                output = []
                in_format = ''
                for i in range(len(info_bitmap)):
                    if info_bitmap[i] == '1':
                        if i <= 12: in_format += 'f '
                        else: in_format += 'i '
                        output.append(data[i])
                if in_format == '':
                    return
                else:
                    in_format = in_format[:-1]

                if len(output) == 0:
                    output = None

                send_message(conn,
                             in_format=in_format,
                             values=output)

            elif data == ac.VEH_GET_LEADER:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')
                leader = aimsun_api.AKIVehGetLeaderId(veh_id)
                send_message(conn, in_format='i', values=(leader,))

            elif data == ac.VEH_GET_FOLLOWER:
                send_message(conn, in_format='i', values=(0,))
                veh_id, = retrieve_message(conn, 'i')
                follower = aimsun_api.AKIVehGetFollowerId(veh_id)
                send_message(conn, in_format='i', values=(follower,))

            elif data == ac.VEH_GET_NEXT_SECTION:
                send_message(conn, in_format='i', values=(0,))
                veh_id, section = retrieve_message(conn, 'i i')
                next_section = AKIVehInfPathGetNextSection(veh_id, section)
                send_message(conn, in_format='i', values=(next_section,))

            elif data == ac.VEH_GET_ROUTE:
                send_message(conn, in_format='i', values=(0,))
                # veh_id, = retrieve_message(conn, 'i')
                # TODO

            elif data == ac.TL_GET_IDS:
                send_message(conn, in_format='i', values=(0,))

                data = None
                while data is None:
                    data = conn.recv(256)

                num_meters = aimsun_api.ECIGetNumberMeterings()
                if num_meters == 0:
                    output = '-1'
                else:
                    meter_ids = []
                    for i in range(1, num_meters + 1):
                        struct_metering = ECIGetMeteringProperties(i)
                        meter_id = struct_metering.Id
                        meter_ids.append(meter_id)
                    output = ':'.join([str(e) for e in meter_ids])
                send_message(conn, in_format='str', values=(output,))

            elif data == ac.TL_SET_STATE:
                send_message(conn, in_format='i', values=(0,))
                meter_aimsun_id, state = retrieve_message(conn, 'i i')
                time = AKIGetCurrentSimulationTime()  # simulation time
                sim_step = AKIGetSimulationStepTime()
                identity = 0
                ECIChangeStateMeteringById(
                    meter_aimsun_id, state, time, sim_step, identity)
                send_message(conn, in_format='i', values=(0,))

            elif data == ac.TL_GET_STATE:
                send_message(conn, in_format='i', values=(0,))
                meter_aimsun_id = retrieve_message(conn, 'i')
                lane_id = 1  # TODO double check
                state = ECIGetCurrentStateofMeteringById(
                    meter_aimsun_id, lane_id)
                send_message(conn, in_format='i', values=(state,))

            elif data == ac.GET_EDGE_NAME:
                send_message(conn, in_format='i', values=(0,))

                # get the edge ID in flow
                edge = None
                while edge is None:
                    edge = conn.recv(2048)

                if isinstance(edge, bytes):
                    edge = edge.decode()
                
                model = GKSystem.getSystem().getActiveModel()
                edge_aimsun = model.getCatalog().findByName(
                    edge, model.getType('GKSection'))

                if edge_aimsun:
                    send_message(conn, in_format='i',
                             values=(edge_aimsun.getId(),))
                else:
                    send_message(conn, in_format='i',
                            values=(int(edge),))

            # in case the message is unknown, return -1001
            else:
                send_message(conn, in_format='i', values=(-1001,))

    # close the connection
    conn.close()


def AAPILoad():
    """Execute commands while the Aimsun template is loading."""
    print("AAPILoad")
    return 0


def AAPIInit():
    """Execute commands while the Aimsun instance is initializing."""
    # set the simulation time to be very large
    print("AAPIInit")
    AKISetEndSimTime(2e6)
    return 0


def AAPISimulationReady():
    """Execute commands when the Aimsun instance has finished initialization."""
    print("AAPISimulationReady")
    return 0


def AAPIManage(time, timeSta, timeTrans, acycle):
    """Execute commands before an Aimsun simulation step."""
    # tcp/ip connection from the aimsun process
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('localhost', PORT))

    # connect to the Flow instance
    server_socket.listen(10)
    c, address = server_socket.accept()

    # start the threaded process
    start_new_thread(threaded_client, (c,))
    
    # print("AAPIManage:: THREAD CLIENT")

    return 0


def AAPIPostManage(time, timeSta, timeTrans, acycle):
    """Execute commands after an Aimsun simulation step."""
    return 0


def AAPIFinish():
    """Execute commands while the Aimsun instance is terminating."""
    return 0


def AAPIUnLoad():
    """Execute commands while Aimsun is closing."""
    return 0


def AAPIPreRouteChoiceCalculation(time, timeSta):
    """Execute Aimsun route choice calculation."""
    return 0


def AAPIVehicleStartParking(idveh, idsection, time):
    """Called when a vehicle starts a parking maneuver."""
    return 0


def AAPIEnterVehicle(idveh, idsection):
    """Execute command once a vehicle enters the Aimsun instance."""
    global entered_vehicles
    entered_vehicles.append(idveh)
    return 0


def AAPIExitVehicle(idveh, idsection):
    """Execute command once a vehicle exits the Aimsun instance."""
    global exited_vehicles
    exited_vehicles.append(idveh)
    return 0


def AAPIEnterPedestrian(idPedestrian, originCentroid):
    """Execute command once a pedestrian enters the Aimsun instance."""
    return 0


def AAPIExitPedestrian(idPedestrian, destinationCentroid):
    """Execute command once a pedestrian exits the Aimsun instance."""
    return 0


def AAPIEnterVehicleSection(idveh, idsection, atime):
    """Execute command once a vehicle enters the Aimsun instance."""
    return 0


def AAPIExitVehicleSection(idveh, idsection, atime):
    """Execute command once a vehicle exits the Aimsun instance."""
    return 0


def AAPIInternalName():
    """Returns the unique internal name of the API. It is called when registering APIs before simulation."""
    return "FlowAimsunAPIV2"
