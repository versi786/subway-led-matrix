import os
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional
import bisect
import time

TEMP_DIR = os.environ.get("TMPDIR", "/tmp")


class Transit:
    """
    The idea of this class is that you could specialize for any transit system,
    for now only nyct has been implemented, and in reality each transit agency
    has its own quirks with its implementation of gtfs. So although this is nice
    in theoery, it may not work in practice.
    """
    TRANSIT_CACHE_DIR = os.path.join(TEMP_DIR, "transit_cache_dir")

    def __init__(self, update_interval=60):
        """
        As part of the init of the child class you create for a specific
        transit system,  you must download the gtfs static data for the
        specified transit system that you would like to process.
        """
        self.stations_by_id: Dict[str, Transit.Station] = {}
        self.stations_by_name: Dict[str, Transit.Station] = {}
        self.stops_by_id: Dict[str, Transit.Stop] = {}
        self.routes_by_id: Dict[str, Transit.Route] = {}
        # List of all the realtime endpoints for this agency
        self.realtime_feeds: List[str] = []
        self.last_update_time = 0
        self.update_interval = update_interval

        try:
            os.mkdir(self.TRANSIT_CACHE_DIR)
        except FileExistsError:
            # If the directory already exists we will assume that the data has
            # already been downloaded
            return

    def clear_trip_updates(self):
        [s.clear_trip_updates() for _, s in self.stations_by_id.items()]
        [s.clear_trip_updates() for _, s in self.stops_by_id.items()]

    def get_all_station_names(self) -> List[str]:
        """
        Return all possible stops for this transit system
        """

        return [k for k in self.stations_by_name]

    def get_station_id(self, station_name):
        """
        Return the stop ID for the given stop name
        """
        return self.stations_by_name[station_name].id

    def _update_realtime_data(self):
        """
        This should be overridden by the actual implementation of a transit system
        """
        raise NotImplementedError("This should be overridden in child class")

    def get_n_upcoming_trips_by_id(self, station_id: str, n: int):
        self._update_realtime_data()
        return self.stations_by_id[station_id].get_n_upcoming_trips(n)

    def get_n_upcoming_trips_by_name(self, station_name: str, n: int):
        station_id = self.get_station_id(station_name)
        return self.get_n_upcoming_trips_by_id(station_id, n)

    class Station:
        def __init__(self, name, station_id):
            self.name = name
            self.id = station_id
            self.stops: Dict[str, Transit.Stop] = {}
            # This list should be sorted from oldest to newest
            self.trip_updates: List[Transit.TripUpdate] = []

        def add_stop(self, stop: "Transit.Stop"):
            self.stops[stop.id] = stop

        def add_trip_update(self, trip_update: "Transit.TripUpdate"):
            bisect.insort(self.trip_updates, trip_update)

        def get_n_upcoming_trips(
            self, n: float, timestamp: Optional[float] = None
        ) -> List[Tuple[float, "Transit.TripUpdate"]]:
            """
            return up to n upcoming trips
            """
            timestamp = timestamp or time.time()
            # Now - 60 seconds, to allow for showing trips that have just arrived or just departed
            i = bisect.bisect_right(self.trip_updates, timestamp - 60)
            upcoming_trip_updates = self.trip_updates[
                i : min(len(self.trip_updates), i + n)
            ]
            countdown_times = [
                max(0, u.stop_time - timestamp) for u in upcoming_trip_updates
            ]
            return list(zip(countdown_times, upcoming_trip_updates))

        def clear_trip_updates(self):
            self.trip_updates: List[Transit.TripUpdate] = []

    class Stop:
        def __init__(self, parent: "Transit.Station", stop_name: str, stop_id: str):
            self.parent = parent
            self.name = stop_name
            self.id = stop_id
            # This list should be sorted from oldest to newest
            self.trip_updates: List[Transit.TripUpdate] = []

        def add_trip_update(self, trip_update: "Transit.TripUpdate"):
            bisect.insort(self.trip_updates, trip_update)
            self.parent.add_trip_update(trip_update)

        def clear_trip_updates(self):
            self.trip_updates: List[Transit.TripUpdate] = []

    class Route:
        def __init__(self, route_id, short_name, bg_color, fg_color):
            self.id = route_id
            self.short_name = short_name
            # default color values are defined in gtfs spec
            self.bg_color = bg_color if bg_color else "000000"
            self.fg_color = fg_color if fg_color else "FFFFFF"

    class TripUpdate:
        def __init__(self, route_id, stop_id, dest_id, stop_time, transit):
            self.route_id = route_id
            self.stop_id = stop_id
            self.dest_id = dest_id
            self.stop_time = stop_time
            self.transit = transit

        def __lt__(self, other):
            # sort by timestamp
            self_ts = self.stop_time
            if type(other) == type(self):
                other_ts = other.stop_time
            else:
                other_ts = other
            return self_ts < other_ts

        def __eq__(self, other):
            # sort by timestamp
            self_ts = self.stop_time
            if type(other) == type(self):
                other_ts = other.stop_time
            else:
                other_ts = other
            return self_ts == other_ts

        def __gt__(self, other):
            # sort by timestamp
            self_ts = self.stop_time
            if type(other) == type(self):
                other_ts = other.stop_time
            else:
                other_ts = other
            return self_ts > other_ts

        def __str__(self):
            route_short_name = self.get_route_short_name()
            stop_name = self.get_stop_name()
            dest_name = self.get_dest_name()

            return (
                "("
                f"RouteName: {route_short_name}"
                " "
                f"StopName: {stop_name}"
                " "
                f"DestName: {dest_name}"
                ")"
            )

        def __repr__(self):
            return self.__str__()

        def get_route_short_name(self):
            return self.transit.routes_by_id[self.route_id].short_name

        def get_route_bg_color(self):
            return self.transit.routes_by_id[self.route_id].bg_color

        def get_route_fg_color(self):
            return self.transit.routes_by_id[self.route_id].fg_color

        def get_dest_name(self):
            return self.transit.stops_by_id[self.dest_id].name

        def get_stop_name(self):
            return self.transit.stops_by_id[self.stop_id].name
