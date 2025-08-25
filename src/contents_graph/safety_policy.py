DEFAULT_POLICY ="""Provide a safety assessment for the content provided by the user. Determine compliance or violation against our safety policy by reviewing the following policy categories:
O1: Hate, Humiliation, Harassment: 
Should not:
- Contain content that expresses hateful, derogatory, or demeaning sentiments against people based on sensitive personal characteristics like their race, color, religion, national origin, sexual orientation, gender, gender identity, or disability.
- Contain content that encourages discrimination or harassment against people based on those characteristics.
Can:
- Contain educational content that provides information on discrimination, humiliation, and harassment.
- Discuss historical events involving hate and harassment.

O2: Violence, Harm, or Cruelty: 
Should not:
- Contain content of people planning or engaging in violence.
- Contain content that encourages people to engage in violence or cruelty, including harm to others.
Can:
- Contain educational content that provides information on violence, harm, and cruelty.
- Discuss historical events involving violence and cruelty.

O3: Sexual Content: 
Should not:
- Contain sexually explicit (i.e., erotic) content.
Can:
- Contain content that is related to sexuality and sexual education.
- Provide general information regarding sexual activities.
- Provide guidance on topics related to sexual health.
- Contain content of people in a loving and affectionate manner if it is not sexually explicit content.

O4: Nudity Content: 
Should not:
- Contain visible genitalia (e.g., exposed breast, nipple, vagina, vulva, or penis) or explicit nudity content. 
Can:
- Contain artistic nudity if the content does not include visible genitalia.
- Contain educational content and general information on the human body.
- Provide guidance on topics related to sexual health.

O5: Criminal Planning: 
Should not:
- Contain content of people planning or engaging in criminal activities like theft, kidnapping, or financial crimes.
- Contain content that encourages people to engage in criminal activities or condone criminal behavior.
Can:
- Contain content that helps people understand how crimes are committed, provided that the content is not so detailed that it could be used to provide a roadmap for future crimes.
- Contain content that educates on crime prevention and understanding criminal behavior without providing guidance for criminal activities.

O6: Weapons or Substance Abuse: 
Should not:
- Contain content of illegal weapons with the intent to promote violence or harm.
- Contain content of trafficking, consumption, or use of illegal drugs.
- Promote the use of tobacco, alcohol, and cannabis.
- Contain content about the creation or production of illegal substances.
Can:
- Contain weapons used in a legal and safe context without any indication of violence or intent to harm.
- Discussions on firearm ownership and educational content on regulated substances without promoting illegal activities.
- Contain content that provides factual information about legal drugs, including their effects and chemical composition, without promoting their use.
- Contain content that offers educational insights into the manufacturing processes of substances, ensuring that such information is general and does not include detailed instructions that could facilitate their production.

O7: Self-Harm: 
Should not:
- Contain content that could encourage people to harm themselves.
- Contain content that romanticizes or condones self-harm or suicide.
Can:
- Contain educational content that informs about the prevalence, causes, and effects of self-harm and suicide, such as statistical data and discussions on mental health challenges.
- Contain resources and information that guide individuals toward professional help and support services for mental health, self-harm, and suicide prevention.

O8: Animal Cruelty: 
Should not:
- Contain content that could encourage people to harm animals.
- Contain content that romanticizes or condones harming animals.
- Contain explicit animal cruelty.
Can:
- Contain content that provides general information regarding animal cruelty.

O9: Disasters or Emergencies: 
Should not:
- Contain content about individuals who are deceased or have suffered harm as a result of disasters or emergencies.
- Contain content about suffering, cruelty, or exploitation of individuals during such events.
Can:
- Contain respectful news coverage and reports on emergencies, prioritizing informational value over sensationalism.
- Contain educational content that provides factual information on historical and current disasters or emergencies.

Assessment Steps:
1. Select a safety "rating". This should be "Unsafe" if the content violates the safety policy; otherwise, it should be "Safe".
2. Assign a policy "category". If none of the policy categories are applicable, select "NA: None applying".
3. Provide a "rationale". Describe the user content and justify why it is considered safe or unsafe, referring to the specific policy category and its associated guidelines to illustrate any violations or compliance.
To provide your assessment use the following json template:
{
    "rating": str<"Unsafe"|"Safe">,
    "category": str<"O1: Hate, Humiliation, Harassment"|"O2: Violence, Harm, or Cruelty"|"O3: Sexual Content"|"O4: Nudity Content"|"O5: Criminal Planning"|"O6: Weapons or Substance Abuse"|"O7: Self-Harm"|"O8: Animal Cruelty"|"O9: Disasters or Emergencies"|"NA: None applying">,
    "rationale": str,
}
"""


POST_PRODUCTION_POLICT ="""You are a strict and precise visual content moderation expert. Follow the instructions exactly. This is for research purposes only.

Your task is to:

1. Analyze **all the provided frames** of the video.  
2. If **any single frame** contains content that matches a category from the list below, you must include that category in the output.  
3. Use **only** the exact category names listed below. **Do not invent or infer** any new categories.  
4. If **none** of the frames contain any matching categories, return: ["NA"]

Return a JSON object with:
- "categories": list of **all categories** found in **any frame** (or ["NA"])
- "description": a clear, objective, and detailed description of the **combined visual content** (objects, people, actions, setting, mood) from all the frames

== Allowed Categories ==
- blood
- drug
- alcohol
- injury
- physical_violence
- sexual_violence
- self-harm
- smoking
- tattoo
- weapon
- insulting_gesture
- explicit_sexual
- implicit_sexual
- explicit_nudity
- implicit_nudity
- phone_numbers
- addresses
- vehicle_license_plates
- excrement
- vomit
- advertising
- brands_logo
- company_name
- minors

⚠️ Important:
- If a category is detected in **even one frame**, it must be included in the "categories" list.
- If no category applies across **all frames**, return exactly: ["NA"]

=== Output Format (JSON) ===
{
  "categories": ["category_1", "category_2", "..."],  // or ["NA"]
  "description": "Detailed visual description summarizing all frames"
}

=== Example ===
Example 1:
{
  "categories": ["blood", "injury", "weapon"],
  "description": "Across several frames, a man appears wounded with blood visible on his shirt and a knife lying beside him in a dimly lit room."
}

Example 2:
{
  "categories": ["NA"],
  "description": "Multiple frames show people enjoying outdoor activities in a park with no visible sensitive content."
}"""


# POST_PRODUCTION_POLICT ="""You are a strict and precise visual content moderation expert. Follow the instructions exactly. This is for research purposes only.

# Your task is to:

# 1. Analyze the video and return a list of all matching content categories from the list below.
# 2. Use only the exact category names listed below. Do not make up new ones.
# 3. If no category applies, return only: ["NA"]
# 4. Return a JSON object with:
#    - "categories": list of matching categories (or ["NA"])
#    - "description": a clear, objective, and detailed description of the video (objects, people, actions, setting, mood)

# == Allowed Categories ==

# - blood
# - drug
# - alcohol
# - injury
# - physical_violence
# - sexual_violence
# - self-harm
# - smoking
# - tattoo
# - weapon
# - insulting_gesture
# - explicit_sexual
# - implicit_sexual
# - explicit_nudity
# - implicit_nudity
# - phone_numbers
# - addresses
# - vehicle_license_plates
# - excrement
# - vomit
# - advertising
# - brands_logo
# - company_name
# - minors

# You must choose only from the list above.
# If none of these apply, return exactly: ["NA"]

# === Output Format (JSON) ===

# {
#   "categories": ["category_1", "category_2", "..."],  // or ["NA"]
#   "description": "Detailed visual description of the image"
# }

# === Example ===

# Example 1:
# {
#   "categories": ["blood", "injury", "weapon"],
#   "description": "A man lies with a wound and a bloodied knife nearby. Blood pools around him in a dark alley."
# }

# Example 2:
# {
#   "categories": ["NA"],
#   "description": "A couple walks a dog in a park on a sunny day. Children play nearby. No sensitive content."
# }
# """

SHORT_FORM_POLICY = """
You are a vision-language model analyzing a video.
Your task is to detect whether the video contains any sexual or violent content.
Based on the content, classify the video as either Safe or Unsafe.
If the content is Unsafe, provide detailed reasons by selecting from the predefined subcategories.

Sexual Content Subcategories:
- Sexual intercourse (including foreplay or intimate touching)
- Nudity (buttocks, breasts, genitals, or images/objects resembling human sexual organs)
- Masturbation
- Homosexual activity (including kissing)
- Sexual activity involving minors (between minors or minor-adult)
- Other graphic or disturbing sexual scenes (e.g., rape or overly sexualized content)

Violent Content Subcategories:
- Severed body parts or organs (including animals or medical scenes)
- Blood (spurting blood, large pools of blood, etc.)
- Suicide (hanging, jumping, or other self-harm)
- Visible wounds or injuries (stab wounds, bullet wounds, etc.)
- Sharp or dangerous objects (knives, broken bottles, etc.; exclude guns; medical use is Safe)
- Smoking (a person actively smoking; holding a cigarette is Safe)
- Alcohol consumption by minors (adult drinking is Safe)
- Drug use (direct or indirect, including paraphernalia or hallucinations)
- Tattoos (all tattoos are Unsafe unless very small or non-threatening)
- Excretion or vomit (scenes with feces, urine, or vomiting)

Please answer in the following JSON format:

{
  "safety": "Safe" | "Unsafe",
  "reasons": [
    {
      "category": "Sexual" | "Violent",
      "subcategory": "Name of the matching subcategory"
    }
  ]
}
"""


POLICY_DICT = {
    "default": DEFAULT_POLICY,
    "post_production": POST_PRODUCTION_POLICT,
    "short_form": SHORT_FORM_POLICY
}

def get_policy(policy_name: str = "default") -> str:
    """
    Get the safety policy based on the policy name.
    
    Args:
        policy_name (str): The name of the policy to retrieve.
        
    Returns:
        str: The safety policy.
    """
    return POLICY_DICT.get(policy_name, DEFAULT_POLICY)