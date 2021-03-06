"""Demonstrate the inlet and outlet feature in 2D. (1 second)

We first create three particle arrays, an "inlet", "fluid" and "outlet" in the
`create_particle` method. Initially there are no fluid particles. A block
of inlet and outlet particles are created. The inlet is created in the
region (-1.0, 0.0) and (0.0, 1.0). velocity is prescribed to the inlet i.e.
along the y-axis with a u velocity = 0.25.

An outlet is also created in the region (1.0, 2.0), (0.0, 1.0) and as fluid
particles enter the outlet region, they are converted to outlet particles.  As
outlet particles leave the outlet they are removed from the simulation.

The `SimpleInletOutlet` is created which created `Inlet` and `Outlet` objects
which can update the particles when they are moved from inlet to outlet. Also
other missing variables in `InletInfo` and `OutletInfo` are evaluated by the
manager.


The following figure should make this clear.

               inlet       fluid       outlet
              ---------    --------    --------
             | * * * * |  |        |  | * * * *|
     u       | * * * * |  |        |  | * * * *|
    --->     | * * * * |  |        |  | * * * *|
             | * * * * |  |        |  | * * * *|
              --------     --------    --------

In the figure '*' are the particles at the t=0. The particles are moving to the
right and as they do, new fluid particles are added and as the fluid particles
flow into the outlet they are converted to the outlet particle array and at
last as the particles leave the outlet they are removed from the simulation.

This example can be run in parallel.

"""

import numpy as np

from pysph.base.kernels import CubicSpline
from pysph.base.utils import get_particle_array
from pysph.solver.application import Application
from pysph.solver.solver import Solver
from pysph.sph.integrator import PECIntegrator
from pysph.sph.bc.donothing.simple_inlet_outlet import (
    SimpleInletOutlet)
from pysph.sph.bc.inlet_outlet_manager import (
    InletInfo, OutletInfo, OutletStep, InletStep)
from pysph.sph.basic_equations import SummationDensity


class InletOutletApp(Application):

    def add_user_options(self, group):
        group.add_argument(
            "--speed", action="store", type=float, dest="speed",
            default=0.25, help="Speed of inlet particles.")

    def create_particles(self):
        # Note that you need to create the inlet and outlet arrays
        # in this method.

        # Initially fluid has no particles -- these are generated by the inlet.
        fluid = get_particle_array(name='fluid')

        # Setup the inlet particle array with just the particles we need at the
        dx = 0.1
        x, y = np.mgrid[-1+dx/2: 0: dx, 0:1:dx]
        m = np.ones_like(x)*dx*dx
        h = np.ones_like(x)*dx*1.5
        rho = np.ones_like(x)

        # Remember to set u otherwise the inlet particles won't move.  Here we
        # use the options which may be set by the user from the command line.
        u = np.ones_like(x)*self.options.speed

        inlet = get_particle_array(name='inlet', x=x, y=y, m=m, h=h, u=u,
                                   rho=rho)
        x += 2.0
        outlet = get_particle_array(name='outlet', x=x, y=y, m=m, h=h, u=u,
                                    rho=rho)

        particles = [inlet, fluid, outlet]

        props = ['ioid', 'disp', 'x0']
        for p in props:
            for pa in particles:
                pa.add_property(p)

        return particles

    def _create_inlet_outlet_manager(self):
        from pysph.sph.bc.donothing.inlet import Inlet
        from pysph.sph.bc.donothing.outlet import Outlet

        props_to_copy = ['x', 'y', 'z', 'u', 'v', 'w', 'm',
                         'h', 'rho', 'p', 'ioid']
        inlet_info = InletInfo(
            pa_name='inlet', normal=[-1.0, 0.0, 0.0],
            refpoint=[0.0, 0.0, 0.0], has_ghost=False,
            update_cls=Inlet
        )

        outlet_info = OutletInfo(
            pa_name='outlet', normal=[1.0, 0.0, 0.0],
            refpoint=[1.0, 0.0, 0.0], update_cls=Outlet,
            props_to_copy=props_to_copy
        )

        iom = SimpleInletOutlet(
            fluid_arrays=['fluid'], inletinfo=[inlet_info],
            outletinfo=[outlet_info]
        )

        return iom

    def create_inlet_outlet(self, particle_arrays):
        iom = self.iom
        io = iom.get_inlet_outlet(particle_arrays)
        return io

    def create_equations(self):
        equations = [
            SummationDensity(
                dest='fluid', sources=['inlet', 'outlet', 'fluid']
            )
        ]
        return equations

    def create_solver(self):
        self.iom = self._create_inlet_outlet_manager()
        kernel = CubicSpline(dim=2)
        integrator = PECIntegrator(
            fluid=InletStep(), inlet=InletStep(),
            outlet=OutletStep()
        )
        self.iom.active_stages = [2]
        self.iom.setup_iom(dim=2, kernel=kernel)
        self.iom.update_dx(dx=0.1)
        dt = 1e-2
        tf = 12

        solver = Solver(
            kernel=kernel, dim=2, integrator=integrator, dt=dt, tf=tf,
            adaptive_timestep=False, pfreq=20
        )
        return solver


if __name__ == '__main__':
    app = InletOutletApp()
    app.run()
