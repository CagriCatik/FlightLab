# Part 3: Aerodynamics Analysis

## Overview

This section documents the **aerodynamic analysis process** of the 3D-printed RC aircraft using **SolidWorks Flow Simulation**. The goal is to evaluate lift, drag, stability, and pressure distribution across the airframe to ensure the aircraft achieves a high lift-to-drag ratio and stable flight characteristics.

Analysis focuses on the **main wing**, **fuselage**, **tail surfaces**, and **winglets**. Computational fluid dynamics (CFD) simulations are used to visualize airflow, detect pressure zones, and extract aerodynamic coefficients for optimization.

---

## Key Steps

1. Prepare the SolidWorks model (remove internal voids, confirm watertight geometry).  
2. Define airflow domain, boundary conditions, and parameters (velocity, density, viscosity).  
3. Run initial CFD to observe pressure and velocity distribution.  
4. Extract lift and drag coefficients for the wing and full model.  
5. Identify high-drag regions or separated flow.  
6. Refine geometry (airfoil, taper, sweep, dihedral).  
7. Re-simulate and validate stability at multiple angles of attack.

---

## Simulation Setup

### Environmental Conditions

| Parameter | Symbol | Value | Units |
|------------|---------|--------|-------|
| Air Density | `ρ` | 1.225 | kg/m³ |
| Dynamic Viscosity | `μ` | 1.7894×10⁻⁵ | kg/(m·s) |
| Airspeed | `V` | 15 | m/s |
| Pressure Outlet | — | 0 | Pa (gauge) |

### Governing Equations

The aerodynamic force coefficients are computed as:

$$
C_L = \frac{L}{\tfrac{1}{2} \rho V^2 S}
$$

$$
C_D = \frac{D}{\tfrac{1}{2} \rho V^2 S}
$$

where:

- \( C_L \) = lift coefficient  
- \( C_D \) = drag coefficient  
- \( L, D \) = lift and drag forces  
- \( \rho \) = air density  
- \( V \) = free-stream velocity  
- \( S \) = reference wing area

The lift-to-drag ratio is expressed as:

$$
\frac{L}{D} = \frac{C_L}{C_D}
$$

---

## Boundary Conditions and Meshing

- Computational domain: at least **5×** the aircraft length in front and behind the model.  
- Mesh type: **adaptive**, refined near leading edges and control surfaces.  
- Cell size: start coarse (~10 mm), refine to 3–5 mm in critical regions.  
- Enable **curvature refinement** on wing tips and sharp geometry.

---

## Post-Processing and Analysis

1. Visualize **pressure contours** on upper and lower wing surfaces.  
2. Generate **velocity streamlines** to inspect flow separation zones.  
3. Compute aerodynamic coefficients \( C_L \) and \( C_D \) for each angle of attack:  

   | AoA | \( C_L \) | \( C_D \) | \( C_L / C_D \) |
   |-----|------------|------------|----------------|
   | 0°  | — | — | — |
   | 5°  | — | — | — |
   | 10° | — | — | — |

4. Evaluate results to identify the best aerodynamic efficiency region.

---

## Optimization Process

- Adjust **wing aspect ratio**, **leading-edge sweep**, and **dihedral angle**.  
- Smooth wing-to-fuselage intersections to reduce interference drag.  
- Re-run simulations to confirm improvements in both \( C_L \) and \( C_D \).  
- Target a consistent lift-to-drag ratio within expected flight Reynolds numbers.

---

## Troubleshooting

| Issue | Possible Cause | Solution |
|--------|----------------|-----------|
| Geometry not watertight | Unmerged bodies or gaps | Use *Check Geometry* and seal openings |
| Solver divergence | Mesh too coarse or AoA too high | Refine mesh, reduce time step |
| Negative lift | Incorrect coordinate orientation | Align axes with flight direction |
| Long simulation time | Excess detail in model | Suppress internal components |
| Flow separation artifacts | Sharp junctions | Apply fillets or smooth transitions |

---

## References

- *SolidWorks Flow Simulation Technical Reference*  
- *NACA Airfoil Data Series* (e.g., NACA 2412, Clark Y)  
- Anderson, J. D. — *Introduction to Flight*  
- *ICAO Standard Atmosphere Tables*  
- Prior RC aircraft CFD case studies for validation
