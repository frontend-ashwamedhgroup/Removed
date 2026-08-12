DEFAULT_DISCLAIMER = (
    'AI screening only. Confirm important decisions with a qualified agriculture officer or plant '
    'pathologist. Use only products registered for the crop and problem in your location, follow the '
    'label exactly, wear required protective equipment, observe pre-harvest intervals, and protect '
    'pollinators, water sources, children and animals.'
)


KNOWN_MULTIWORD_CROPS = (
    "bell pepper",
    "sweet potato",
    "dragon fruit",
    "green gram",
    "black gram",
    "common bean",
)


def split_class_name(class_name):
    """Split both PlantVillage-style and plain-text crop/disease labels."""
    raw = str(class_name or "").strip()
    if '___' in raw:
        crop, disease = raw.split('___', 1)
    elif '__' in raw:
        crop, disease = raw.split('__', 1)
    elif raw.startswith('Onion_'):
        crop, disease = 'Onion', raw[len('Onion_'):]
    else:
        cleaned = raw.replace('_', ' ').replace(',', ' ')
        cleaned = ' '.join(cleaned.split())
        lower = cleaned.casefold()
        crop = ''
        disease = ''
        for known_crop in KNOWN_MULTIWORD_CROPS:
            prefix = known_crop.casefold() + ' '
            if lower.startswith(prefix):
                crop = cleaned[:len(known_crop)]
                disease = cleaned[len(known_crop):].strip()
                break
        if not crop:
            parts = cleaned.split(maxsplit=1)
            crop = parts[0] if parts else 'Unknown crop'
            disease = parts[1] if len(parts) > 1 else 'Unknown condition'

    crop = crop.replace('_', ' ').replace(',', '').strip()
    disease = disease.replace('_', ' ').strip() or 'Unknown condition'
    return crop, disease


def _healthy(crop, disease):
    return {
        'summary': f'The image most closely matches a healthy {crop} class.',
        'symptoms': 'No model-recognized disease pattern was dominant in this image.',
        'immediate_actions': 'Continue scouting. Check the underside of leaves and several plants before concluding the crop is healthy.',
        'organic_options': 'No curative spray is recommended solely from a healthy prediction. Maintain balanced nutrition, irrigation and field hygiene.',
        'chemical_options': 'Do not apply a pesticide without a confirmed target problem. Unnecessary spraying wastes money and can harm beneficial organisms.',
        'prevention': 'Use clean planting material, proper spacing, crop rotation, sanitation and regular field monitoring.',
        'disclaimer': DEFAULT_DISCLAIMER,
    }


def guidance_for(class_name):
    crop, disease = split_class_name(class_name)
    text = disease.lower()
    if 'healthy' in text:
        return _healthy(crop, disease)

    base = {
        'summary': f'The model detected a pattern most similar to {disease} in {crop}.',
        'symptoms': 'Compare the prediction with symptoms on several plants and inspect both leaf surfaces, stems, roots and bulbs/fruits when relevant.',
        'immediate_actions': 'Mark affected areas, photograph symptoms clearly, remove severely affected material where practical, avoid moving contaminated tools, and request expert confirmation when spread is rapid or confidence is low.',
        'organic_options': 'Improve airflow and drainage, avoid unnecessary leaf wetness, sanitize tools, remove infected debris, rotate crops, and use locally approved biological or botanical options only when the label includes the crop and target.',
        'chemical_options': 'After confirmation, an agriculture professional may select a locally registered product with an appropriate mode of action. Rotate mode-of-action groups and follow the label; this portal does not prescribe a dose.',
        'prevention': 'Use resistant varieties where available, certified planting material, balanced fertilization, correct spacing, clean irrigation, crop rotation and routine scouting.',
        'disclaimer': DEFAULT_DISCLAIMER,
    }

    if any(k in text for k in ('virus', 'mosaic', 'yellow leaf curl')):
        base.update({
            'symptoms': 'Look for mosaic or mottled colour, curling, distortion, stunting and uneven growth. Viral symptoms can resemble nutrient or herbicide injury.',
            'immediate_actions': 'Isolate and remove strongly symptomatic plants when practical. Control weed hosts and identify insect vectors. Do not propagate from affected plants.',
            'organic_options': 'Use insect-proof nurseries, reflective mulch where suitable, clean tools, resistant varieties and vector exclusion. Manage weeds around the field.',
            'chemical_options': 'There is no curative pesticide for a plant virus. Vector management may reduce spread but will not cure infected plants; use only locally registered vector-control products after identification.',
            'prevention': 'Use certified virus-free seed/transplants, resistant varieties, vector monitoring, sanitation and rapid removal of infection sources.',
        })
    elif any(k in text for k in ('bacterial', 'citrus greening', 'haunglongbing')):
        base.update({
            'symptoms': 'Typical bacterial problems may show water-soaked spots, angular lesions, yellow halos, ooze, cankers or rapid tissue collapse. Citrus greening often causes blotchy asymmetric mottling and poor fruit development.',
            'immediate_actions': 'Avoid working in wet plants, disinfect tools, reduce overhead irrigation, remove heavily affected tissue where recommended, and seek confirmation because bacterial and fungal spots can look similar.',
            'organic_options': 'Prioritize sanitation, clean seed/transplants, airflow, drip irrigation and removal of volunteer hosts. Copper-based products may be allowed in some systems but must be label-approved.',
            'chemical_options': 'Copper-based bactericides or other locally registered bactericides may suppress some bacterial diseases but resistance and crop injury are possible. Citrus greening requires official/local management of infected trees and psyllid vectors.',
            'prevention': 'Use certified clean material, resistant varieties, crop rotation, clean water and tools, and avoid handling plants while foliage is wet.',
        })
    elif any(k in text for k in ('mite', 'caterpillar')):
        base.update({
            'symptoms': 'Inspect closely for insects, mites, eggs, webbing, feeding scars, holes, frass and damage concentrated on new growth or leaf undersides.',
            'immediate_actions': 'Confirm the pest and life stage before treatment. Record infestation levels and protect natural enemies. Remove isolated heavily infested leaves where practical.',
            'organic_options': 'Use field sanitation, physical removal, water sprays where suitable, traps, conservation of beneficial insects, and a registered biological such as Bt for susceptible caterpillar stages when appropriate.',
            'chemical_options': 'Choose a selective insecticide or miticide registered for the crop and identified pest. Rotate mode-of-action groups and avoid repeated unnecessary applications.',
            'prevention': 'Scout weekly, manage weeds, use clean seedlings, avoid excessive nitrogen and conserve beneficial organisms.',
        })
    elif any(k in text for k in ('downy mildew', 'powdery mildew')):
        base.update({
            'symptoms': 'Mildews commonly produce pale or yellow patches with powdery or downy growth, often more visible on one leaf surface. Confirm under suitable humidity conditions.',
            'immediate_actions': 'Improve airflow, remove badly affected leaves, reduce prolonged leaf wetness and avoid dense canopy conditions.',
            'organic_options': 'Use resistant varieties, wider spacing, sanitation and label-approved biologicals or mineral products appropriate to the specific mildew.',
            'chemical_options': 'A locally registered mildew fungicide may be needed. Downy and powdery mildews require different fungicide groups, so confirm the diagnosis before selection and rotate modes of action.',
            'prevention': 'Monitor weather risk, irrigate at times that allow foliage to dry, avoid overcrowding and start protection early in high-risk periods.',
        })
    elif any(k in text for k in ('rust',)):
        base.update({
            'symptoms': 'Look for orange, brown or dark pustules, often on the underside of leaves, with corresponding yellow areas above.',
            'immediate_actions': 'Remove volunteer host plants, improve airflow and avoid transporting spores on wet clothing or tools.',
            'organic_options': 'Plant resistant varieties, remove crop debris and volunteer hosts, rotate crops and use approved biological products where effective.',
            'chemical_options': 'A registered rust fungicide may be considered after confirmation. Apply preventively or early according to the label and rotate fungicide groups.',
        })
    elif any(k in text for k in ('rot', 'fusarium')):
        base.update({
            'symptoms': 'Inspect roots, stem bases, bulbs or fruit for softening, discoloration, odour, vascular browning or dry decay. Several pathogens and storage conditions can cause rot.',
            'immediate_actions': 'Remove affected plants or stored produce, improve drainage and ventilation, avoid injury, and separate healthy material from diseased material.',
            'organic_options': 'Use clean planting stock, well-drained soil, crop rotation, sanitation, careful harvest handling and approved biological soil treatments where locally validated.',
            'chemical_options': 'Fungicides rarely restore already-rotted tissue. Seed, soil or post-harvest treatments may help prevent specific confirmed pathogens when registered and correctly timed.',
            'prevention': 'Avoid waterlogging and wounds, cure bulbs correctly, sanitize storage areas, maintain recommended storage temperature/humidity and rotate away from susceptible hosts.',
        })
    elif any(k in text for k in ('blight', 'leaf spot', 'black rot', 'esca', 'scorch', 'target spot', 'cercospora')):
        base.update({
            'symptoms': 'Look for expanding spots, concentric rings, dark margins, yellow halos, scorched areas or rapid leaf/tissue death. Pattern, weather and crop stage help distinguish similar diseases.',
            'immediate_actions': 'Remove badly infected debris where practical, reduce splash and leaf wetness, improve airflow, sanitize tools and avoid overhead irrigation late in the day.',
            'organic_options': 'Use crop rotation, clean seed/transplants, resistant varieties, mulching to reduce soil splash, sanitation and approved biological protectants.',
            'chemical_options': 'After diagnosis, a registered protectant or systemic fungicide may be selected. Common active-ingredient groups used for some leaf spots/blights include copper compounds, dithiocarbamates, chloronitriles, strobilurins or triazoles, but crop labels and resistance guidance determine suitability.',
            'prevention': 'Start with clean material, rotate crops, manage residue, space plants correctly, monitor weather and alternate fungicide modes of action when treatments are justified.',
        })

    return base
