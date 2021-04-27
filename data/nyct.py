import logging
import os
import requests
import zipfile
import io
import csv
from data.transit import Transit
import gtfs_realtime_pb2
import nyct_subway_pb2
import time
from google.protobuf.message import DecodeError


class NYCT(Transit):

    NYCT_CACHE_DIR = os.path.join(Transit.TRANSIT_CACHE_DIR, "nyct")
    MTA_GTFS_URL = (
        "https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs{feed_group}"
    )

    def __init__(self, update_interval=60):
        super().__init__()
        self.MTA_API_KEY = os.getenv("MTA_API_KEY")
        assert self.MTA_API_KEY, (
            "Must specify environment variable MTA_API_KEY or update `.env` file"
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self._download_gtfs_data()
        self._parse_static_data()
        feed_groups = [
            "",  # 123456
            "-ace",
            "-bdfm",
            "-g",
            "-jz",
            "-nqrw",
            "-l",
            "-7",
            "-sir",
        ]
        self.realtime_feeds = [
            self.MTA_GTFS_URL.format(feed_group=f) for f in feed_groups
        ]
        self.last_update_time = 0

    def _download_gtfs_data(self):
        # url to the zip file containing MTA metadata
        DATA_URL = "http://web.mta.info/developers/data/nyct/subway/google_transit.zip"
        res = requests.get(DATA_URL)
        res.raise_for_status()
        try:
            os.mkdir(self.NYCT_CACHE_DIR)
        except FileExistsError:
            # If the directory already exists we will assume that the data has
            # already been downloaded
            return

        with zipfile.ZipFile(io.BytesIO(res.content)) as google_transit:
            for filename in google_transit.namelist():
                filepath = os.path.join(self.NYCT_CACHE_DIR, filename)
                with open(filepath, "wb") as outfile:
                    outfile.write(google_transit.read(filename))
                    self.logger.debug(filepath)

    def _parse_static_data(self):
        # TODO this can probably be shared in the base transit class
        # Reference: https://developers.google.com/transit/gtfs/reference#stopstxt
        with open(os.path.join(self.NYCT_CACHE_DIR, "stops.txt")) as f:
            rows = [row for row in csv.DictReader(f)]

        for row in rows:
            if row["location_type"] == "0":
                # Stop (or Platform)
                parent = self.stations_by_id[row["parent_station"]]
                stop = Transit.Stop(parent, row["stop_name"], row["stop_id"])
                parent.add_stop(stop)
                self.stops_by_id[stop.id] = stop
                # Stop names are duplicates so this is why we do not save
                # a Dict of stops_by_name
            if row["location_type"] == "1":
                # Station
                station = Transit.Station(row["stop_name"], row["stop_id"])
                self.stations_by_id[station.id] = station
                self.stations_by_name[station.name] = station

        # Reference: https://developers.google.com/transit/gtfs/reference#routestxt
        with open(os.path.join(self.NYCT_CACHE_DIR, "routes.txt")) as f:
            rows = [row for row in csv.DictReader(f)]

        for row in rows:
            route = Transit.Route(
                row["route_id"],
                row["route_short_name"],
                row["route_color"],
                row["route_text_color"],
            )
            self.routes_by_id[route.id] = route

    def _update_realtime_data(self):
        now = time.time()
        if now - self.last_update_time < self.update_interval:
            # Do not call transit system api more than every 60 seconds
            return
        else:
            self.last_update_time = now

        # Clear the data from the previous update
        self.clear_trip_updates()

        # NOTE this takes about 3-5 seconds to update all feeds. A future
        # enhancement Could be to run the updates in a background thread, so
        # that the user can always retrieve the latest cached data for 'free'
        # add the new data from realtime feed
        for feed in self.realtime_feeds:
            self._update_route_realtime_data(feed)

    def _update_route_realtime_data(self, feed):
        # NOTE this should only be called from _update_realtime_data
        # TODO a alot of these fields can probably be moved to the base class
        # this class should only be concerned with adding the specific nyct updates

        feed_message = self._get_feed_message(feed)
        if not feed_message:
            return

        # Reference: https://developers.google.com/transit/gtfs-realtime/reference#message-feedentity
        # pylint: disable=no-member # Protobuf does not play nice with pylint
        for feed_entity in feed_message.entity:

            # trip_update is only required if not CANCELED
            if feed_entity.HasField("trip_update"):
                # Refrence: https://developers.google.com/transit/gtfs-realtime/reference#message-tripupdate
                trip_update = feed_entity.trip_update
                # Trip Update contains a list of StopTimeUpdate which updates
                # the arrival / departure time for this Trip at every stop
                # along the trip

                trip_descriptor = trip_update.trip
                if trip_descriptor.HasField("schedule_relationship"):
                    if (
                        trip_descriptor.schedule_relationship
                        == gtfs_realtime_pb2.TripUpdate.StopTimeUpdate.ScheduleRelationship.CANCELED
                    ):
                        # TODO remove this trip?
                        continue

                stop_time_updates = trip_update.stop_time_update
                if not len(stop_time_updates):
                    # skip if list is empty
                    continue

                dest_id = stop_time_updates[-1].stop_id
                for stop_time_update in stop_time_updates:
                    stop_time = (
                        stop_time_update.arrival.time
                        if stop_time_update.HasField("arrival")
                        else stop_time_update.arrival.time
                    )

                    stop_id = stop_time_update.stop_id
                    trip_update = Transit.TripUpdate(
                        trip_descriptor.route_id, stop_id, dest_id, stop_time, self
                    )

                    if stop_id in self.stops_by_id:
                        self.stops_by_id[stop_id].add_trip_update(trip_update)
                    else:
                        self.logger.info("Missing stop {stop_id} in stops.txt")

    def _get_feed_message(self, feed):
        data = requests.get(
            feed,
            headers={"x-api-key": self.MTA_API_KEY},
        )
        if data.status_code != 200:
            raise RuntimeError(data.text)

        # Parse Protobuf Data
        # Reference: https://developers.google.com/transit/gtfs-realtime/reference#message-feedmessage
        feed_message = gtfs_realtime_pb2.FeedMessage()
        try:
            feed_message.ParseFromString(data.content)
        except DecodeError:
            return None
        return feed_message


if __name__ == "__main__":
    nyct = NYCT()
    station_names = ["Lexington Av/53 St", "51 St"]
    for station_name in station_names:
        upcoming_trip_updates = nyct.get_n_upcoming_trips_by_name(station_name, 3)
        print(upcoming_trip_updates)
