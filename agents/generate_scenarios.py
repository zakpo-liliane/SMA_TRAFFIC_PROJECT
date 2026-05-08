import random

def generer_routes(n_veh=100):
    with open("routes.rou.xml", "w") as f:
        f.write("<routes>\n")

        f.write('<vType id="car" accel="1.0" decel="4.5" maxSpeed="13.9"/>\n')

        for i in range(n_veh):
            depart = random.randint(0, 900)
            route = random.choice([
                "E1 E2",
                "E2 E3",
                "E3 E4",
                "E4 E1"
            ])

            f.write(f'''
<vehicle id="veh{i}" type="car" depart="{depart}">
<route edges="{route}"/>
</vehicle>
''')

        f.write("</routes>")