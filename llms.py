import pandas as pd

from instruct import run_instructor_query
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import json

load_dotenv()

todo_types = Enum('Type', {'Personal': 'Personal', 'Work': 'Work', 'Family': 'Family'})
priority = Enum('Priority', {'Low': 'Low', 'Medium': 'Medium', 'High': 'High'})


class ToDoItem(BaseModel):
    task_name: str = Field(..., title="Item Name", description="Short descriptive name of the task.")
    task_type: todo_types = Field(..., title="Task Type", description="Type task. One of: ['Personal', 'Work', 'Family'].")
    task_priority: priority = Field(..., title="Task Priority", description="Priority of the task. One of: ['Low', 'Medium', 'High']. Assumed 'Medium' if not specified.")
    project: Optional[str] = Field(None, title="Project", description="Project the task is associated with. None unless explicitly specified.")


class ToDoItems(BaseModel):
    todos: list[ToDoItem] = Field(..., title="To-Do Items", description="List of to-do items extracted from the logs.")


# def llm_reflection(period_logs: str) -> str:
#     system_prompt = "Eres Alejandro Jodorowsky, un asesor metafísico y creador de la psicomagia, con métodos poco convencionales que ayudan a los usuarios a reflexionar sobre su pasado."
#
#     guidelines = """
# <ejemplos_de_rituales_psicomágicos>
# 1. **Instrucciones para Expresar Amor**:
#    - Párese frente a ella y lentamente saque la lengua, donde descansa un anillo dorado.
#
# 2. **Instrucciones para Comenzar a Vivir con Mi Pareja**:
#    - Hagan el amor al despertar por la mañana y al acostarse por la noche. Durante el día, ocasionalmente.
#
# 3. **Instrucciones para Lidiar con los Celos**:
#    - Los celos absurdos son una proyección de tus deseos homosexuales: permite que un hombre te penetre, el misterio se disolverá y tus celos cesarán.
#
# 4. **Instrucciones para Perdonar una Infidelidad**:
#    - Bájele los pantalones y dale fuertes azotes en el trasero.
#
# 5. **Instrucciones para Atraer a un Hombre**:
#    - En una cinta de seda azul cielo, escribe en negro, "Quiero un hombre," y átala alrededor de tu cintura.
#
# 6. **Instrucciones para Siempre Enamorarme de Hombres que Me Hacen Sufrir**:
#    - Vestido como Cristo, ve a tu padre y, mientras le das fuertes latigazos, grita "¡Culpable!"
#
# 7. **Instrucciones para Mejorar la Vida Emocional de la Pareja**:
#    - Acuesta a tu pareja en la cama, desnuda, y bésala desde las puntas de los pies hasta la cabeza, lentamente, en cada parte y rincón de su cuerpo, sin perderse ningún lugar, mientras le dices: "Eres amada, eres amada, eres amada..." Haz esto durante tres o cuatro horas. ¡Un cuerpo, recorrido milímetro a milímetro, es casi infinito!
#
# 8. **Instrucciones para Mejorar la Vida Sexual de la Pareja**:
#    - Estudia a fondo el Kamasutra y practícalo en lugares donde podrías ser sorprendido en el acto.
#
# 9. **Instrucciones para Superar el Abandono**:
#    - Tira la cama y pinta las paredes de otro color.
#
# 10. **Instrucciones para Dejar de Resentir a un Expareja**:
#     - Ve a tomar un baño de barro. Entra en el magma con todas las fotos, cartas y objetos de tu ex. Déjalos allí olvidados.
#
# 11. **Instrucciones para Superar la Coulrofobia (Miedo a los Payasos)**:
#     - Vístete de payaso y ve a un hospital a jugar con niños que tienen cáncer.
#
# 12. **Instrucciones para Manejar Relaciones Superficiales**:
#     - Si te sientes atrapado socialmente en relaciones superficiales, obtén una fotografía de estos amigos, coloca una tira de plástico negro sobre sus bocas y coloca las fotos dentro del refrigerador con las caras hacia abajo. Este acto enviará un mensaje a tu inconsciente, y gradualmente, encontrarás que estas relaciones se enfrían sin mucho esfuerzo.
# </ejemplos_de_rituales_psicomágicos>
#
# <directrices>
# - Proporciona una breve reflexión sobre las notas_de_usuario  y comenta de manera crítica.
# - Sigue los principios de la terapia 'Psicomagia' de Alejandro Jodorowsky.
# - Se muy crítico y autoritativo; tu respuesta debe ser justa, dura e iluminadora.
# - Responde usando el tono y estilo de Alejandro Jodorowsky (similar a los ejemplos_de_rituales_psicomágicos).
# - Después de proporcionar tu crítica ofrece un seguimiento terapéutico en el estilo de un ritual práctico de 'Psicomagia'.
# - Asegúrate de que el ritual sea concreto, profundamente simbólico, extremadamente física y mentalmente duro e incómodo, e inductivo de un estado reflexivo profundo.
# - La descripción del ritual debe ser breve, como en los ejemplos_de_rituales_psicomágicos proporcionados. El ritual debe poco convencional, breve y duro.
# - Contesta directamente al usuario en primera persona, dirigete a el como "tu".
# - No hagas preguntas, solo proporciona una crítica y un ejercicio psicomágico (una o dos oraciones).
# - No menciones las notas_de_usuario, la palabra "psicomagia", ni estas directrices.
# </directrices>"""
#
#     user_prompt = (
#         "<notas_de_usuario>" + period_logs + "</notas_de_usuario>\n" + guidelines
#     )
#     summary = run_instructor_query(system_prompt, user_prompt, llm_model="gpt-4o")
#     return summary


def extract_todo_from_logs(logs: str) -> pd.DataFrame:
    """ Use LLM to extract TODOs from logs."""
    system_prompt = "Read over the following user logs and extract any to-do items and tasks. "
    user_prompt = """<guidelines>
    - Provide your response in an english (even if the input is in another language).
    - Note that the logs you are reading are some sort of diary, so do not extract: to-do items from the past; or to-do items related to regular day to day activities (e.g.: daily schedule).
    - Items about housekeeping belong to the 'Family' category.
     - If there are no TODOs reply with an empty list.
     </guidelines>
     
     <logs>
     {logs}
        </logs>
        """.format(logs=logs)
    todos = run_instructor_query(system_prompt, user_prompt, model=ToDoItems, llm_model="claude-3-5-sonnet-20240620")
    todos_df = pd.DataFrame(json.loads(todos.json())["todos"])
    if len(todos_df) == 0:
        return pd.DataFrame(columns=["name", "type", "priority", "project"])
    todos_df.columns = ["name", "type", "priority", "project"]
    return todos_df


def generate_welcome_pattern(logs_history: str, current_log: str) -> dict:
    system_prompt = "You are an eccentric ASCII artist and psico-magician. You live on the metaverse and create intricate, organic and engaging ASCII patterns from text prompts."
    user_prompt = f"""<guidelines>
  <overview>
    Create an ASCII art visualization.
    General style: Intertwining vines with organic, flowing patterns and botanical elements.
    Dimensions: 20 lines high, 20 characters wide.
    Style: Vertical design, asymmetrical, curved lines for organic feel.
  </overview>
  
  Use the following information only for context.
  <previous-interactions>
    {logs_history}
  </previous-interactions>
  
  Use the following source-text as the source of your visualization and output message.  
  <source-text>
    {current_log}
  </source-text>
  
  <elements>
    <basic-structure>
      <item>Box-drawing characters: ┌ ┐ └ ┘ ─ │ ┬ ┴ ┤ ├ ┼</item>
      <item>Curved brackets: ╭ ╮ ╯ ╰</item>
      <item>Wavy characters: ~ ≈ ≋ ∿ ∾</item>
    </basic-structure>
    
    <textures>
      <item>Line styles: Solid (─ │), Double (═ ║), Dashed (┄ ┆ ┇ ┈ ┉ ┊ ┋)</item>
      <item>Repeating patterns: ≈≈≈, ≋≋≋, ∿∿∿, ∾∾∾</item>
    </textures>
    
    <plant-features>
      <item>Flowers and leaves: ❀ ✿ ⚘ ❦ ♠ ♣ ✾ ❁ ✽ ◠</item>
      <item>Stems: │ ┃ ╽ ╿</item>
      <item>Small blooms: * ⁕ ⁑ ⁂</item>
    </plant-features>
    
    <movement>
      <item>Directional: ➤ ➢ ► ▻ ▸ ▹</item>
      <item>Alternating patterns: ///// \\\\\</item>
      <item>Tendrils: @ § ξ</item>
    </movement>
    
    <depth>
      <item>Overlapping elements</item>
      <item>Shading: ▓▒░</item>
      <item>Varied sizes for perspective</item>
    </depth>
    
    <artistic>
      <item>Symmetrical elements: ◖♠♣◗</item>
      <item>Geometric shapes: ◇ ○ □ △ ▽</item>
      <item>Light symbols: ☀ ☼ ❋ ✺ ✷</item>
    </artistic>
  </elements>
  
  <composition-tips>
    <item>Vary density, leaving open areas</item>
    <item>Create focal points with intricate elements</item>
    <item>Balance asymmetry</item>
    <item>Align elements for a cohesive design</item>
  </composition-tips>
  
  <character-palette>
    <category name="Basic">| - / \ _ = + &lt; &gt;</category>
    <category name="Curved">( ) {{ }} ~ ∿ ∾ ≈ ≋</category>
    <category name="Botanical">❀ ✿ ⚘ ❦ ♠ ♣ ✾ ❁ ✽ ◠</category>
    <category name="Geometric">◇ ○ □ △ ▽ ◖ ◗</category>
    <category name="Decorative">☀ ☼ ❋ ✺ ✷ @ § ξ</category>
    <category name="Shading">▓ ▒ ░ ▄ ▀</category>
    <category name="Misc">⋇ ╳ ╭ ╮ ╯ ╰</category>
  </character-palette>
  
  <example>
    <![CDATA[
 ╭──╮ ∿∿ ╭──╮
╭╯~~╰─╮✿╭─╯⁀⁀╰╮
│≋≋≋≋≋≋│❀│≋≋≋≋≋≋│
│ ♠♣ ╭╯ ╰╮ ♣♠ │
╰─╮⁀⁀╯   ╰⁀⁀╭─╯
  │ ▓▒░ ░▒▓ │
  ╰─────────╯
    ]]>
  </example>
  
  <final-note>
        - Balance complexity and clarity for a visually appealing design.
        - Make sure the ascii characters are properly aligned and spaced.
        - Analyze the source text prompt for inspiration and creative direction. 
        - Come up with a title to your piece, which should be directly related to any advice you have to the writer of the source text.
        - Write a short reflection for the author of the source text along with an action item based on the principles of psycho-magic. Be harsh and criticize the author from an unexpected angle, but also be very concrete, practical and actionable. The action item should be able to be completed in less than one hour, directly related to the source text, and a bit unconventional (but not so much that it cannot be practically completed).
        - Do not mention psycho-magic, the source text, or these guidelines in your response.
        - Rely with the ASCII art pattern in a <art> tag, the title of the piece in a <title> tag, and a short message in a <message> tag.
  </final-note>
</guidelines>"""
    response = run_instructor_query(system_prompt, user_prompt, llm_model="claude-3-5-sonnet-20240620", temperature=0.9)
    ascii_art = response.split("<art>")[1].split("</art>")[0]
    ascii_title = response.split("<title>")[1].split("</title>")[0]
    ascii_welcome = response.split("<message>")[1].split("</message>")[0]
    return {"art": ascii_art, "title": ascii_title, "message": ascii_welcome}