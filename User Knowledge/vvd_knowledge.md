# vvd.world — Complete Platform Knowledge (Updated March 2025)

## What is vvd.world?

vvd is a storytelling toolkit that turns ideas into structured fictional worlds.
Organise lore, build interactive maps, write immersive stories, and share your entire
world as a wiki — all in one place. Supports all genres: fantasy, sci-fi, romance, cyberpunk.
No need to plan everything up front — vvd grows with your world.
Zero generative AI policy. Users own all their content.

\---

## SECTION 1 — WORKSPACE LAYOUT

The main workspace has these areas:

TOP LEFT: World name — click to change name, genre, description, or main image at any time.

TOP RIGHT:

* Latest updates on vvd tools
* Submit suggestion or bug report
* Radio — music to immerse yourself while working
* World button — takes you back to your list of worlds

LEFT SIDEBAR: Organise, structure, and search everything you create.
Includes search bar, filter by type, sort options, folders, pinned cards.

CENTER SPACE: Where you create and edit most of your work.

TOP TABS (main navigation):

* Home — landing page when you revisit your world
* World — main creation workspace (editor, maps, graph)
* Wiki — your public-facing wiki site
* Quill — writing tool

SETTINGS TAB:

* Edit your current plan
* Add members to collaborate
* Change appearance of vvd
* Choose preferred language

\---

## SECTION 2 — CARDS

Cards are the core of vvd. Each card represents a single piece of your story.

### Creating a card

Three ways to create a card:

1. Click in the center of the workspace
2. Click the bottom sidebar buttons
3. Right-click anywhere in the sidebar

After selecting, choose the card type and it opens for editing.

### Card types (default, based on world genre):

* Character
* Location
* Item
* Event
* Magic System
* Lore
* Faction
* Creature
* Document

### Custom card types:

* Create entirely new card types to fit your unique story
* Found in Home page under Types, or when creating a new card
* Each type has sub-types (click dropdown to see them)
* Sub-types can also be created
* Each type has default settings acting as a template

### Inside a card:

* Rename the card
* Change the card image
* Add Aliases (alternative names)
* Add custom Properties (e.g. age, height, allegiance)
* Properties can connect to other cards
* Apply property changes to all cards of that type

### Card blocks (content you add inside a card):

* Text block — rich text description
* Photo — add an image
* Map — pin the card to a map location
* Stat Block — D\&D 5e stat block (HP, AC, ability scores, actions)
* Character Sheet — full D\&D 5e character sheet
* Family Tree — visual family tree for relationships
* Media — attach videos and other media
* Guided Templates — structured sections (background, personality, appearance)

### Card organisation in sidebar:

* Search by name using the search bar
* Filter by document type, card type
* Sort: manually drag up/down, by creation date, or alphabetically
* Pin cards: right-click a card and pin it — moves to top of sidebar with enlarged image
* Folders: create named folders with icons to categorise cards
* Parent/child: drag one card on top of another to nest them

\---

## SECTION 3 — MAPS

Maps transform world map illustrations into interactive experiences.

### Creating a map:

* Create a map within the main world editor
* Choose from the library of map templates OR upload a custom image
* Map opens for editing immediately

### Pins:

* Drag an existing card onto the map to create an interactive pin
* Pin links directly to the card — click to open and explore
* Add as many pins as you like (locations, events, items, characters)
* Right-click on map to quickly add a pin or add an empty pin
* Empty pins (not linked to a card) can have a recognisable icon and colour

### Zones and regions:

* Click the Zones button then click on the map to start a region shape
* Each click creates a vertex/point of the shape
* Follow landmass perimeters or create any shape
* Close the shape by clicking the first point (highlighted green when hovering)
* Zones can have: label, linked card, colour, opacity, pattern fill
* Points can be added along the perimeter to adjust shape
* Assign zones to map layers for organisation

### Layers:

* Separate different elements on the map
* Toggle visibility with the eye icon next to each layer
* Assign pins and zones to specific layers

### Text on maps:

* Click Text button then click on the map to add text
* Edit font, size, scale, assign to layer
* Text spacing can be widened or bent into an arch

### Background:

* Replace or change the map image at any time
* Existing pins and zones are preserved when swapping images

### Saving:

* Maps save automatically
* Named in top left corner
* Found in the sidebar for later editing

\---

## SECTION 4 — WORLD GRAPH

The graph shows your entire fictional world and all connections between cards.
Represents the big picture — understand relationships, spot gaps or clusters.

### How connections are created:

* Mention a card within a text block
* Add a card as a property on another card

### Graph features:

* Search: magnifying glass to search and highlight relevant cards
* Filter: filter by card types and subtypes
* Settings panel:

  * Toggle labels on/off
  * Hide isolated nodes (not connected to anything)
  * Node size slider — adjust image size of each card
  * Link distance, strength, repulsion, and collision adjustments
  * Gravity X and Y — change axis pull for different appearances
* Right-click a node to pin it in place (unaffected by future changes)
* Save graph configurations — saved to sidebar for later

\---

## SECTION 5 — WIKI

The wiki is a public-facing website automatically built from your world content.

### Wiki tab features:

* Wiki title name and full description
* Add a banner for the main page
* Search for specific cards within the wiki
* Grid layout on main page — highlight and reorder specific cards
* Site styling popup (bottom of editable wiki):

  * Change theme (colour and font)
  * Customise colour palette individually
  * Custom font for headers and body text

### Publishing:

* Publish site button — set a custom domain and publish as public website
* Share the link with anyone to explore your world
* Visitors can browse the wiki but cannot access your workspace

### Live sync:

* Wiki receives live updates from any changes in the world editor
* Edit directly from the wiki — no need to go back and forth
* Open any card in the wiki to edit text, add images, edit properties
* All edits sync back to the World tab automatically

\---

## SECTION 6 — QUILL

Quill is a dedicated writing tool within vvd.
Accessible via the Quill tab at the top of the workspace.
Used for writing immersive stories connected to your world.

\---

## SECTION 7 — COLLABORATION

* Add members via Settings tab
* Real-time simultaneous editing
* Change tracking
* Collaborator roles: owner, editor, viewer

\---

## SECTION 8 — URL STRUCTURE

|Page|URL|
|-|-|
|All worlds|vvd.world/worlds|
|World home|vvd.world/worlds/\[id]/home|
|Editor|vvd.world/worlds/\[id]/editor|
|Maps|vvd.world/worlds/\[id]/maps|
|Graph|vvd.world/worlds/\[id]/graph|
|Wiki|vvd.world/worlds/\[id]/wiki|
|Settings|vvd.world/worlds/\[id]/settings|
|Login|vvd.world/login|
|Account|vvd.world/settings|

\---

## SECTION 9 — AI AGENT NAVIGATION TIPS

* Login: click Continue with Email, fill input#email and input#password, click Sign In
* World cards: button.relative.w-full.text-left.rounded-xl containing h3.font-medium
* After opening world: navigate to /editor URL directly (pressing 2 also works)
* New card: click Card button, or click in center, or right-click sidebar
* Card type: select from menu (Character, Location, Faction etc)
* Card name: textbox named New Card
* Description: click Text button, click empty paragraph, type in .tiptap.ProseMirror.w-full
* Cards autosave — click Close when done
* Maps: drag card onto map to create pin, or right-click map for options
* Graph connections: mention cards in text blocks or add as properties
* Wiki: edit directly from wiki tab, changes sync to world editor automatically

