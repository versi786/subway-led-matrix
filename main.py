import argparse
import time
import sys
import os

from rgbmatrix import graphics
from data.nyct import NYCT

from renderer.base import Base

from dotenv import load_dotenv
from renderer import upcoming_trains

load_dotenv()


class SubwaySign(Base):
    def __init__(self, *args, **kwargs):
        super(SubwaySign, self).__init__(*args, **kwargs)
        self.nyct = NYCT()
        self.parser.add_argument(
            "--stop",
            dest="stops",
            help="The name of a stop you would like to monitor",
            action="append",
        )
        self.parser.add_argument(
            "--list-stops",
            dest="list_stops",
            help="List all possible stops and exit",
            action="store_true",
        )

    def run(self) -> bool:
        font = graphics.Font()
        font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/7x13.bdf")

        if self.args.list_stops:
            stations = self.nyct.get_all_station_names()
            out = "\n".join(sorted(stations))
            print(out)
            return True

        if not self.args.stops:
            print(
                "Please provide at least one stop by adding --stop argument\n"
                "For example add: --stop 'World Trade Center' --stop 'York St'"
            )
            return False

        print("Press CTRL-C to exit")

        while True:
            station_names = self.args.stops
            for station_name in station_names:
                upcoming_trip_updates = self.nyct.get_n_upcoming_trips_by_name(
                    station_name, 3
                )
                upcoming_trains.upcoming_trains.render(
                    self.matrix, 10, upcoming_trip_updates
                )


# Main function
if __name__ == "__main__":
    subwaySign = SubwaySign()
    subwaySign.process()
