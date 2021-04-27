from rgbmatrix import graphics
import time
from renderer.utils import convert_hex_to_color

font = graphics.Font()
font.LoadFont("/home/pi/rpi-rgb-led-matrix/fonts/5x8.bdf")


class upcoming_trains:
    @staticmethod
    def render(matrix, max_render_time, upcoming_trip_updates):
        offscreen_canvas = matrix.CreateFrameCanvas()
        # TODO this should do something fancy for scrolling text
        # so each inner loop should be shorter than 5 seconds.
        # Need to think of a reasonable way to scroll each line independently
        start = time.time()
        end = start + max_render_time
        num_rows = 3
        row_height = 10
        divider_height = 1
        # Total height = 32
        # train height = 10
        # divider heigt = 1
        # train height = 10
        # divider heigt = 1
        # train height = 10
        offscreen_canvas = matrix.CreateFrameCanvas()

        if len(upcoming_trip_updates) < num_rows:
            print("Not enough upcoming trips for stop")
            return
        while time.time() < end:

            offscreen_canvas.Fill(0, 0, 0)
            for row_num in range(num_rows):
                # Draw background for trains
                row_min_y = (row_height + divider_height) * row_num # (closer to origin)
                row_max_y = row_min_y + row_height # closer to bottom
                eta, trip = upcoming_trip_updates[row_num]
                fg_color = convert_hex_to_color(trip.get_route_fg_color())
                bg_color = convert_hex_to_color(trip.get_route_bg_color())
                text_color = graphics.Color(255,255,255)

                # Fill in background color of train
                for i in range(row_min_y, row_max_y):
                    graphics.DrawLine(
                        offscreen_canvas,
                        x1=0,
                        y1=i,
                        x2=5,
                        y2=i,
                        color=bg_color,
                    )

                x = 1
                y = row_max_y - 2 # move up 2 bixels from bottom

                # Draw route number/letter
                w = graphics.DrawText(
                    offscreen_canvas,
                    font,
                    x,
                    y,
                    fg_color,
                    trip.get_route_short_name(),
                )

                x += w
                x += 1

                # Draw eta
                eta = str(int(eta // 60)) + "m"
                w = graphics.DrawText(
                    offscreen_canvas,
                    font,
                    x,
                    y,
                    text_color,
                    eta,
                )
                x += w
                x += 2

                # Draw Destination
                w = graphics.DrawText(
                    offscreen_canvas, font, x, y, text_color, trip.get_dest_name()
                )

            offscreen_canvas = matrix.SwapOnVSync(offscreen_canvas)
            offscreen_canvas.Clear()
            time.sleep(1)
