# Kolorowanka: paint by numbers (iPad + Apple Pencil)

The whole app is the **`app`** folder. It runs in Safari on an iPad, and once added to the
home screen it opens like a regular app: with its own icon, full screen, and no internet needed.

Besides the built-in pictures, you can **upload your own photos**: the app turns them into
a paint-by-numbers page (outlines, regions and numbers) on the device, without internet and
without sending the photo anywhere. Details in
[Your own photos as coloring pages](#your-own-photos-as-coloring-pages).

The app UI is in Polish; button names are quoted below in Polish with an English gloss.

There are 10 built-in pictures (each has 870–1610 regions):

| Category   | Pictures |
|------------|----------|
| Mandalas   | Lotus mandala, Star mandala, Stained-glass rosette, Garden mandala (the hardest) |
| Landscapes | Sunset over a lake, Fairy-tale castle, Balloons over a valley |
| Animals    | Underwater world, Butterfly in a garden, Owl in the moonlight |

---

## Installing on the iPad (permanent, recommended)

The app has to be put online once so the iPad can download it. The easiest way is the free
**Netlify** service: you drag the folder onto a page and that's it.

**On the Mac:**

1. Open **https://app.netlify.com/drop** in a browser.
2. Create a free account or log in (e.g. with Google or e-mail).
3. In Finder, open `claude_projects` → `kolorowanka`. Drag the **`app`** folder onto the
   drop area on the Netlify page.
4. After a few seconds you get an address like `https://something-123abc.netlify.app`.
   You can change it to something easier: **Site configuration → Change site name**
   (e.g. `kolorowanka-mine`, giving `https://kolorowanka-mine.netlify.app`).

**On the iPad:**

5. Open that address in **Safari**.
6. Tap the **Share** button (a square with an up arrow), then **"Add to Home Screen"**.
   If an **"Open as Web App"** toggle appears, leave it on. Finally tap **Add**.
7. From now on, launch Kolorowanka from the home screen icon. The first time, the iPad
   needs internet to download the pictures (about 5 MB). After that it also works offline.

Your painting progress is saved on the iPad, inside the app. Don't clear this site's data in
Safari settings, or you will lose your colored pictures.

---

## Quick test without an account (iPad and Mac on the same Wi-Fi)

1. On the Mac, open **Terminal** and run:
   ```bash
   cd ~/claude_projects/kolorowanka/app && python3 -m http.server 8000
   ```
2. On the iPad, open **`http://192.168.1.146:8000`** in Safari.
   This is the Mac's address on your home network and it may change. You can check the current
   one in System Settings → Wi-Fi → Details → IP address.
3. This only works while the Mac is on and the command in Terminal is running.
   Strokes painted in test mode will not carry over to the Netlify version.

---

## Your own photos as coloring pages

1. In the gallery, in the **Twoje zdjęcia** (Your photos) section, tap the **Dodaj zdjęcie**
   (Add photo) tile and pick a photo from the iPad library or take a new one.
2. Choose the **number of colors** (12–30) and the **level of detail**:
   - **Mało** (Low): only color blobs from the photo, fewer and larger regions,
   - **Średnio / Dużo / Bardzo dużo** (Medium / High / Very high): large blobs are further split
     into pieces, like stained glass. The number of regions keeps growing
     (roughly 1500 / 3000 / 5500 for a photo with a clear subject).
3. Tap the preview to see the outlines with numbers. Tap again to go back to colors.
4. Enter a name and tap **Dodaj i maluj** (Add and paint).

Converting at "Bardzo dużo" can take up to about a minute. The photo is processed on the iPad,
offline, and is never uploaded anywhere. The finished coloring page stays only in the app on
that iPad. The **Usuń** (Delete) button on a tile removes it from the gallery but does not touch
the original photo in Photos. Photos with a clear subject work best: animals, flowers,
landscapes, portraits.

## How to paint

- **Choosing a picture:** the app opens to a gallery. Tap a picture and start painting.
- **Color:** pick it from the bar at the bottom. The number on the circle matches the numbers
  in the regions. Regions with the selected number are lightly highlighted, so they are easy to find.
- **Pencil:** paints for real, stroke by stroke. Pressing harder gives a slightly thicker stroke.
- **Brush size:** the slider in the bottom right corner.
- **Fingers:** use two fingers to zoom and pan the picture. After the Pencil is first used,
  you can also pan with one finger, and a resting palm does not paint.
- **Two-finger tap** or the **Cofnij** (Undo) button undoes the last stroke.
- **W polu** (In the region, on by default): color stays inside the region where you started
  the stroke, even if the Pencil slips over the line. Turn it off to paint completely freely.
- **Eraser:** wipes off painted color.
- **✓ next to a color** means all regions with that number are already painted.
- **Podgląd** (Preview): shows what the finished picture looks like.
- **Zapisz** (Save): opens the share sheet, where you choose "Save Image" to put the picture in Photos.
- **Od nowa** (Start over, on a gallery tile): clears the picture.

---

## For the curious: where the pictures come from

The pictures are generated by scripts in the `tools` folder (Python with numpy, scipy,
scikit-image and pillow). Each picture is built from shapes that the script splits into regions,
then it picks the position and size of the number in each region. To add another picture, write a
new function in `tools/scenes.py` or `tools/mandalas.py`, add an entry to `PICTURES`, and run
`python build.py <id>`. After every change in the `app` folder, bump the `VERSION` number in
`app/sw.js` and drag the `app` folder onto Netlify again (in your site's **Deploys** tab).
