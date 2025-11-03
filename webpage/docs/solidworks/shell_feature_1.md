# Hollowing a Solid Model Using the Shell Feature

This guide explains how to make the interior of a 3D body hollow while maintaining a defined wall thickness using SolidWorks. The **Shell** feature is the primary method for this task. It allows you to remove material from the interior of a part, leaving a uniform shell thickness suitable for lightweight designs and 3D printing.

---

## 1. Select the Body

1. Open your part in **SolidWorks**.
2. In the **FeatureManager Design Tree**, select the solid body you want to hollow (for example, `Body5`).
3. Ensure that the body is a **solid**, not a **surface**. If it is a surface, convert it first (see Section 6).

---

## 2. Activate the Shell Tool

1. Navigate to the top menu: **Features > Shell**.
2. The **Shell PropertyManager** will appear on the left side of the interface.

---

## 3. Define the Wall Thickness

1. Under the **Parameters** section, specify the desired **wall thickness**.
   Example: `0.8 mm`.
2. This value determines how thick the remaining solid walls will be after the interior is removed.
3. By default, SolidWorks shells **inward** from the existing surfaces.

   * To reverse this behavior, enable **Shell Outward** to expand the shell externally instead.

---

## 4. Specify Open Faces (Optional)

1. If you need the interior to be accessible or open from a particular side:

   * Click the face(s) on the model to remove them during shelling.
   * The selected faces will become openings.
2. For a fully enclosed structure (e.g., a fuselage or enclosed housing):

   * **Do not select any faces**. The interior will be hollow but fully sealed.

---

## 5. Apply the Shell

1. Review the preview visualization to confirm the shell direction and wall thickness.
2. Click the **green checkmark** (`✔`) in the PropertyManager.
3. The part will update, showing the hollow interior with consistent wall thickness.

---

## 6. If the Body Is a Surface

If your model is a **surface body** instead of a solid, the Shell feature cannot be used directly. Convert it first:

1. Go to **Surfaces > Knit Surface** and merge separate surfaces if needed.
2. Use **Features > Thicken** to convert the surface into a solid body.
3. Once the body is solid, proceed with the **Shell** operation as described above.

---

## 7. Handling Shell Failures

Complex models may sometimes fail to shell due to thin features, small fillets, or self-intersecting geometry.
In such cases, use the **Offset Surface** method:

### Alternate Method: Offset Surface + Thicken

1. Go to **Surfaces > Offset Surface**.
2. Enter the desired **offset distance** equal to your wall thickness.
3. Offset the outer surface inward (or outward as required).
4. **Knit** the offset and original surfaces together to close the gaps.
5. Convert the knitted surface to a solid using **Features > Thicken**.

This method gives finer control for complex or delicate geometry where the standard Shell command fails.

---

## 8. Common Shell Parameters

| Parameter                    | Description                                                     |
| ---------------------------- | --------------------------------------------------------------- |
| **Thickness**                | Defines the uniform wall distance (e.g., `0.8 mm`).             |
| **Shell Outward**            | Expands the wall outward instead of removing interior material. |
| **Multi-Thickness Settings** | Allows assigning different wall thicknesses to specific faces.  |

---

## 9. Practical Applications

* **3D Printing:** Creates lightweight, material-efficient designs.
* **Aerospace/Automotive:** Ideal for hollow fuselages, ducts, or housings.
* **Mechanical Design:** Useful for enclosures and casings that need internal space.

---

## Result

The resulting part is hollowed out internally while maintaining the defined wall thickness. This approach ensures structural strength, material savings, and reduced weight—especially useful for additive manufacturing and aerodynamic components.
