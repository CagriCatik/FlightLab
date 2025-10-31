# Part 1: Concept

## Overview

This project focuses on designing and constructing a custom **3D-printed RC aircraft** using **SolidWorks** for CAD modeling and a **Bambu Lab P1S** printer for fabrication. The design reuses existing RC components from a previous build and integrates them into a modular airframe optimized for aerodynamic efficiency, structural strength, and printability.

The RC aircraft is powered by a **BL2215/25 brushless motor**, **9x4.7E propeller**, **40A ESC**, and a **7.8V 2S LiPo battery**. These components determine the design envelope—defining fuselage volume, center of gravity (CG), thrust-to-weight ratio, and overall performance. The build sequence aligns with the complete workflow outlined in the following parts:

1. Concept Design
2. Winglets and Tail Tips
3. Aerodynamics Analysis
4. Slice and Export
5. Structure, Controls, Printing, and Assembly

---

## Key Steps

1. **Define Requirements:**
   Determine design constraints using the electrical and mechanical specifications of the BL2215/25 motor, 9x4.7E propeller, 40A ESC, and 2S LiPo battery.

2. **Model the Airframe in SolidWorks:**
   Develop the main fuselage, wing, and tail geometries with parametric constraints. Include servo mounts, hatches, and component cavities.

3. **Aerodynamic and Structural Validation:**
   Simulate airflow and load response. Validate aerodynamic efficiency and mechanical integrity under expected flight conditions.

4. **Optimize CG and Component Layout:**
   Position internal components to achieve balanced CG at approximately 25–30% of the mean aerodynamic chord.

5. **Prepare STL and Slice for Bambu Lab P1S:**
   Export and slice the model with proper print orientation, infill, and wall thickness settings. Split oversized components for the P1S build volume.

6. **Print and Assemble:**
   3D print all sections, reinforce critical joints, and assemble the airframe with servos, control linkages, and electronics.

7. **Test and Validate:**
   Conduct static thrust, CG, and control surface calibration tests before the maiden flight.

---

## Notes

* Ensure total airframe weight is optimized for a 2S LiPo system.
* Reinforce critical load points near motor mounts, wing roots, and servo beds.
* Design modular connections (e.g., dovetails or magnets) for repair and upgrade flexibility.
* Choose aerodynamic profiles favoring slow flight stability and smooth gliding behavior.
* Verify print dimensions and tolerances specific to the P1S printer.

---

## Materials

* **Filament:** PLA+ or PETG (for rigidity and thermal resistance)
* **Reinforcement:** Carbon fiber rods or 3 mm dowels
* **Motor:** BL2215/25 brushless (approx. 1000–1200 KV)
* **Propeller:** 9x4.7E
* **ESC:** 40A
* **Battery:** 7.8V 2S LiPo
* **Servos:** 9g micro servos (3–4 units)
* **Receiver:** Compatible with RC transmitter
* **Control Accessories:** Pushrods, control horns, and linkages
* **Printer:** Bambu Lab P1S (256×256×256 mm build volume)

---

## Tools

* SolidWorks (CAD modeling and simulation)
* Bambu Studio (slicing software for P1S)
* 3D printer (Bambu Lab P1S)
* Digital calipers
* Soldering station
* Screwdrivers, pliers, cutters
* Epoxy or CA glue (for assembly)

---

## Steps

### **Define Parameters:**

* Specify motor dimensions, propeller clearance, ESC placement, and battery compartment geometry.
* Establish limits for target wingspan, fuselage volume, and total weight.

### **Create CAD Models:**

* Model fuselage, wing, and empennage with internal reinforcement ribs.
* Design servo mounts, access hatches, and cooling channels.
* Apply fillets and chamfers to minimize drag.
* Ensure modular segmentation for P1S print volume limits.

### **Run Simulations:**

* Conduct FEA on structural parts (motor mount, wing root).
* Perform CFD-based airflow simulation to refine lift-to-drag ratio.

### **Export and Slice:**

* Export STL files for each subassembly.
* Slice with 0.2 mm layer height, 3 perimeters, and 20–25% gyroid infill.
* Set PLA+ print temperature to 215°C and bed to 60°C.
* Enable adaptive layer thickness and orient parts to reduce support.

### **Assemble:**

* Dry-fit printed parts to verify tolerances.
* Reinforce key junctions using carbon rods and adhesive.
* Install servos, ESC, receiver, and motor.
* Connect control linkages and verify smooth motion.

### **Test and Adjust:**

* Validate CG position (25–30% chord).
* Run bench motor tests and control calibration.
* Conduct initial glide and controlled powered flights.

---

## Troubleshooting

* **Weak Layer Adhesion:** Raise print temperature or increase wall count.
* **CG Too Far Forward/Backward:** Reposition the battery or adjust fuselage cavity.
* **ESC Overheating:** Improve airflow or reduce prop pitch.
* **Servo Noise or Jitter:** Verify wiring and isolate power signals.
* **Warping:** Ensure bed adhesion or use enclosed print mode on the P1S.

---

## References

* Manufacturer datasheets for BL2215/25 motor and 40A ESC.
* SolidWorks documentation for assembly and simulation.
* Bambu Studio configuration guide for PLA+ and PETG.
* RC aircraft aerodynamic and structural design principles.
