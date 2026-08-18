###### Necesitamos algunos cambios

* 
* Hay que eliminar estas columnas del exel: **ETAPA\_PROCESAL (actual) - FASE\_PROCESAL (actual) - ETAPA\_PROCESAL (migrado) - CODIGO\_FASE - FASE\_PROCESAL (migrado)- FECHA INICIO JUICIO - FECHA INICIAL FASE ACTUAL - DIAS EN LA FASE ACTUAL - ETAPA\_PROCESAL - FASE\_PROCESAL** . 
* A partir de la columna vacia en el lado derecho de COMENTARIO\_ULTIMO comenzaríamos a trabajar con las nuevas columnas. 
* Las columnas que se deberán mostrar en el exel deben ser de esta forma: **FECHA INICIO JUICIO - FECHA FIN ULTIMA FASE: RECOLECCION (fecha\_elegida)- ULTIMA ETAPA** ( DE LO ENCINTRADO) **- ULTIMA FASE** ( DE LO ENCINTRADO) **-** **COPY FECHA FIN ULTIMA FASE CON NOMBRE** (Fecha inicio fase actual) **RECOLECCION - ETAPA ACTUAL (LO QUE SIGUE O SE MANTIENE)- FASE ACTUAL (LO QUE SIGUE DESPUES)**



* Al finalizar la búsqueda y encontrar en que fase y etapa del árbol se encuentra el caso, el sistema también deberá agregar nuevas filas para mostrar cual debería ser la siguiente etapa y fase del caso, esta debe sección debe también contener la fecha de lo ultimo que se encontró respecto al árbol



**ULTIMA ETAPA**

**ULTIMA FASE**

(Fecha fin ultima fase)



**DIAS TRANSCURRIDOS**

(Días transcurridos desde la fecha\_elegida que da el sistema hasta la fecha actual mía, debe mostrar la fecha actual cuando el sistema estuvo operativo fecha\_actual )



**FASE DE ETAPA ACTUAL**

**FASE ACTUAL**

(Fecha inicio fase actual)



Ejemplo: el caso se logra ubicar en "6.2 MANDAMIENTO DE EJECUCION" con fase "6 LIQUIDACION Y EMBARGO", la fecha\_elegida es 21/07/2025,

&#x20;por ende la siguiente columna tendrá FASE DE ETAPA mostrando "6.3 EMBARGO" y ACTUAL FASE ACTUAL mostrando "6 LIQUIDACION Y EMBARGO"



=================================================================================

&#x20;

1. En caso de que la búsqueda me de como resultado remate o congelamiento, el sistema debe dejar en ese mismo estado y no salte a mas mostrando un mensaje como "CASO SOLVENTADO POR (aqui muestra lo que salto como resultado, ya searemate o congelamiento)"
=============================================================================
2. Cuándo exista citación no realizada- reenvío citación-RAZON ENVIO A CITACIONES y no exista un archivo donde diga algo como cita realizada
debe ubicar la demanda en la fase anterior "Calificación..."
=============================================================================
3. Para los casos con  mas de 1 folder en la pantalla de "**Datos generales"** de los folders en caso de existir mas de uno
=============================================================================
4. Solventar problemas del tipo: La consulta no devolvió resultados. Para este caso hay que marcar el caso y toda su fila en rojo, en la parte donde debería ir en que parte del árbol se lo ubico debe haber estar este mensaje "ERROR: NUMERO DE CASO NO DEVOLVIO RESULTADOS. CASO (numero de caso) DEBE SER SOLVENTADO MANUALMENTE"
=============================================================================
5. En caso de que exista ABANDONO POR FALTA DE IMPULSO PROCESAL que revise muy bien la RAZON DE EJECUTORIA ya que puede ser que se esta ejecutando el abandono, por ende se va directo a calificacion....
=============================================================================
6. En caso de llegar a un ACUERDO DE MEDIACIÓN antes de la razon de la ejecutoria si se acepta que el sistema lo guarde como "5.3 SENTENCIA EJECUTORIADA", "etapa": "5 SENTENCIA"
7. En caso de que NOMBRAMIENTO DE PERITO pero no exista informe pericial (escrito) no guardar como "6.1 LIQUIDACION PERITO LIQUIDADOR", "etapa": "6 LIQUIDACION Y EMBARGO" sino como "5.3 SENTENCIA EJECUTORIADA", "etapa": "5 SENTENCIA"

