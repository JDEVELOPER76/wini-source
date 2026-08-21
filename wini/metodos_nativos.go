package wini

import (
	"fmt"
	"regexp"
	"strconv"
	"strings"
)

// MetodoNativo define la firma de un método nativo
type MetodoNativo func(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error)

// ============= MÉTODOS PARA LISTAS =============

func listaAgregar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return nil, fmt.Errorf("agregar requiere al menos 1 argumento")
	}
	return append(lista, args[0]), nil
}

func listaEliminar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return nil, fmt.Errorf("eliminar requiere al menos 1 argumento")
	}
	elemento := args[0]
	resultado := []interface{}{}
	encontrado := false
	for _, v := range lista {
		if !encontrado && v == elemento {
			encontrado = true
			continue
		}
		resultado = append(resultado, v)
	}
	return resultado, nil
}

func listaEliminarEn(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return nil, fmt.Errorf("eliminar_en requiere la posición")
	}
	posicion, err := toInt(args[0])
	if err != nil {
		return nil, fmt.Errorf("la posición debe ser un número")
	}
	if posicion < 0 || posicion >= len(lista) {
		return nil, nil
	}
	elemento := lista[posicion]
	resultado := make([]interface{}, 0, len(lista)-1)
	resultado = append(resultado, lista[:posicion]...)
	resultado = append(resultado, lista[posicion+1:]...)
	return []interface{}{resultado, elemento}, nil
}

func listaEliminarUltimo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(lista) == 0 {
		return nil, nil
	}
	elemento := lista[len(lista)-1]
	resultado := lista[:len(lista)-1]
	return []interface{}{resultado, elemento}, nil
}

func listaInsertar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 2 {
		return nil, fmt.Errorf("insertar requiere posición y elemento")
	}
	posicion, err := toInt(args[0])
	if err != nil {
		return lista, nil
	}
	if posicion < 0 {
		posicion = 0
	}
	if posicion > len(lista) {
		posicion = len(lista)
	}
	resultado := make([]interface{}, len(lista)+1)
	copy(resultado[:posicion], lista[:posicion])
	resultado[posicion] = args[1]
	copy(resultado[posicion+1:], lista[posicion:])
	return resultado, nil
}

func listaExtender(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return nil, fmt.Errorf("extender requiere otra lista")
	}
	if otra, ok := args[0].([]interface{}); ok {
		return append(lista, otra...), nil
	}
	return lista, nil
}

func listaContiene(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return false, nil
	}
	for _, v := range lista {
		if v == args[0] {
			return true, nil
		}
	}
	return false, nil
}

func listaPosicion(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return -1, nil
	}
	for i, v := range lista {
		if v == args[0] {
			return i, nil
		}
	}
	return -1, nil
}

func listaContar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(args) < 1 {
		return 0, nil
	}
	contador := 0
	for _, v := range lista {
		if v == args[0] {
			contador++
		}
	}
	return contador, nil
}

func listaLongitud(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	return len(lista), nil
}

func listaVacia(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	return len(lista) == 0, nil
}

func listaInvertir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	resultado := make([]interface{}, len(lista))
	for i, v := range lista {
		resultado[len(lista)-1-i] = v
	}
	return resultado, nil
}

func listaOrdenar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	resultado := make([]interface{}, len(lista))
	copy(resultado, lista)
	// Ordenar por string para simplicidad
	for i := 0; i < len(resultado); i++ {
		for j := i + 1; j < len(resultado); j++ {
			if fmt.Sprintf("%v", resultado[i]) > fmt.Sprintf("%v", resultado[j]) {
				resultado[i], resultado[j] = resultado[j], resultado[i]
			}
		}
	}
	return resultado, nil
}

func listaOrdenarDesc(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	resultado := make([]interface{}, len(lista))
	copy(resultado, lista)
	for i := 0; i < len(resultado); i++ {
		for j := i + 1; j < len(resultado); j++ {
			if fmt.Sprintf("%v", resultado[i]) < fmt.Sprintf("%v", resultado[j]) {
				resultado[i], resultado[j] = resultado[j], resultado[i]
			}
		}
	}
	return resultado, nil
}

func listaPrimero(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(lista) == 0 {
		return nil, nil
	}
	return lista[0], nil
}

func listaUltimo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(lista) == 0 {
		return nil, nil
	}
	return lista[len(lista)-1], nil
}

func listaLimpiar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	_, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	return []interface{}{}, nil
}

func listaCopiar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	resultado := make([]interface{}, len(lista))
	copy(resultado, lista)
	return resultado, nil
}

func listaATexto(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	separador := ", "
	if len(args) > 0 {
		if s, ok := args[0].(string); ok {
			separador = s
		}
	}
	elementos := make([]string, len(lista))
	for i, v := range lista {
		elementos[i] = fmt.Sprintf("%v", v)
	}
	return strings.Join(elementos, separador), nil
}

func listaSumar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	total := 0.0
	for _, v := range lista {
		switch val := v.(type) {
		case int:
			total += float64(val)
		case float64:
			total += val
		}
	}
	if total == float64(int(total)) {
		return int(total), nil
	}
	return total, nil
}

func listaMaximo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(lista) == 0 {
		return nil, nil
	}
	maximo := lista[0]
	for _, v := range lista[1:] {
		if fmt.Sprintf("%v", v) > fmt.Sprintf("%v", maximo) {
			maximo = v
		}
	}
	return maximo, nil
}

func listaMinimo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	lista, ok := objeto.([]interface{})
	if !ok {
		return nil, fmt.Errorf("no es una lista")
	}
	if len(lista) == 0 {
		return nil, nil
	}
	minimo := lista[0]
	for _, v := range lista[1:] {
		if fmt.Sprintf("%v", v) < fmt.Sprintf("%v", minimo) {
			minimo = v
		}
	}
	return minimo, nil
}

// ============= MÉTODOS PARA CADENAS =============

func cadenaLongitud(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return len(cadena), nil
}

func cadenaMayuscula(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.ToUpper(cadena), nil
}

func cadenaMinuscula(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.ToLower(cadena), nil
}

func cadenaCapitalizar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(cadena) == 0 {
		return cadena, nil
	}
	return strings.ToUpper(cadena[:1]) + strings.ToLower(cadena[1:]), nil
}

func cadenaTitulo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.Title(cadena), nil
}

func cadenaInvertir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	resultado := []rune(cadena)
	for i, j := 0, len(resultado)-1; i < j; i, j = i+1, j-1 {
		resultado[i], resultado[j] = resultado[j], resultado[i]
	}
	return string(resultado), nil
}

func cadenaContiene(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return false, nil
	}
	return strings.Contains(cadena, fmt.Sprintf("%v", args[0])), nil
}

func cadenaIndice(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return -1, nil
	}
	sub := fmt.Sprintf("%v", args[0])
	return strings.Index(cadena, sub), nil
}

func cadenaUltimoIndice(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return -1, nil
	}
	sub := fmt.Sprintf("%v", args[0])
	return strings.LastIndex(cadena, sub), nil
}

func cadenaEmpiezaCon(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return false, nil
	}
	return strings.HasPrefix(cadena, fmt.Sprintf("%v", args[0])), nil
}

func cadenaTerminaCon(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return false, nil
	}
	return strings.HasSuffix(cadena, fmt.Sprintf("%v", args[0])), nil
}

func cadenaContar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return 0, nil
	}
	sub := fmt.Sprintf("%v", args[0])
	return strings.Count(cadena, sub), nil
}

func cadenaReemplazar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 2 {
		return cadena, nil
	}
	viejo := fmt.Sprintf("%v", args[0])
	nuevo := fmt.Sprintf("%v", args[1])
	return strings.ReplaceAll(cadena, viejo, nuevo), nil
}

func cadenaUnir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return cadena, nil
	}
	if lista, ok := args[0].([]interface{}); ok {
		elementos := make([]string, len(lista))
		for i, v := range lista {
			elementos[i] = fmt.Sprintf("%v", v)
		}
		return strings.Join(elementos, cadena), nil
	}
	return cadena, nil
}

func cadenaDividir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	var partes []string
	if len(args) == 0 || args[0] == nil {
		partes = strings.Fields(cadena)
	} else {
		separador := fmt.Sprintf("%v", args[0])
		partes = strings.Split(cadena, separador)
	}
	resultado := make([]interface{}, len(partes))
	for i, p := range partes {
		resultado[i] = p
	}
	return resultado, nil
}

func cadenaRecortar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.TrimSpace(cadena), nil
}

func cadenaRecortarIzquierda(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.TrimLeft(cadena, " \t\n\r"), nil
}

func cadenaRecortarDerecha(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return strings.TrimRight(cadena, " \t\n\r"), nil
}

func cadenaExtraer(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return cadena, nil
	}
	inicio, err := toInt(args[0])
	if err != nil {
		return cadena, nil
	}
	if len(args) == 1 {
		if inicio >= len(cadena) {
			return "", nil
		}
		if inicio < 0 {
			inicio = len(cadena) + inicio
		}
		return cadena[inicio:], nil
	}
	fin, err := toInt(args[1])
	if err != nil {
		return cadena, nil
	}
	if inicio < 0 {
		inicio = len(cadena) + inicio
	}
	if fin < 0 {
		fin = len(cadena) + fin
	}
	if inicio < 0 {
		inicio = 0
	}
	if fin > len(cadena) {
		fin = len(cadena)
	}
	if inicio >= len(cadena) || fin <= inicio {
		return "", nil
	}
	return cadena[inicio:fin], nil
}

func cadenaRepetir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return cadena, nil
	}
	veces, err := toInt(args[0])
	if err != nil {
		return cadena, nil
	}
	if veces <= 0 {
		return "", nil
	}
	return strings.Repeat(cadena, veces), nil
}

func cadenaAEntero(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	cadena = strings.TrimSpace(cadena)
	if val, err := strconv.Atoi(cadena); err == nil {
		return val, nil
	}
	return "0", nil
}

func cadenaADecimal(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	cadena = strings.TrimSpace(cadena)
	if val, err := strconv.ParseFloat(cadena, 64); err == nil {
		return val, nil
	}
	return "0.0", nil
}

func cadenaALista(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	resultado := make([]interface{}, len(cadena))
	for i, r := range cadena {
		resultado[i] = string(r)
	}
	return resultado, nil
}

func cadenaEsNumero(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	cadena = strings.TrimSpace(cadena)
	if _, err := strconv.ParseFloat(cadena, 64); err == nil {
		return true, nil
	}
	return false, nil
}

func cadenaEsDigito(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	for _, r := range cadena {
		if r < '0' || r > '9' {
			return false, nil
		}
	}
	return len(cadena) > 0, nil
}

func cadenaEsAlfabetico(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	for _, r := range cadena {
		if (r < 'a' || r > 'z') && (r < 'A' || r > 'Z') {
			return false, nil
		}
	}
	return len(cadena) > 0, nil
}

func cadenaEsVacia(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	return len(cadena) == 0, nil
}

func cadenaEsPalindromo(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	// Limpiar: solo caracteres alfanuméricos, en minúsculas
	limpio := ""
	for _, r := range cadena {
		if (r >= 'a' && r <= 'z') || (r >= 'A' && r <= 'Z') || (r >= '0' && r <= '9') {
			if r >= 'A' && r <= 'Z' {
				limpio += string(r + 32)
			} else {
				limpio += string(r)
			}
		}
	}
	// Verificar si es palíndromo
	for i := 0; i < len(limpio)/2; i++ {
		if limpio[i] != limpio[len(limpio)-1-i] {
			return false, nil
		}
	}
	return true, nil
}

func cadenaEsMayuscula(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(cadena) == 0 {
		return false, nil
	}
	for _, r := range cadena {
		if r >= 'a' && r <= 'z' {
			return false, nil
		}
	}
	return true, nil
}

func cadenaEsMinuscula(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(cadena) == 0 {
		return false, nil
	}
	for _, r := range cadena {
		if r >= 'A' && r <= 'Z' {
			return false, nil
		}
	}
	return true, nil
}

func cadenaASlug(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	slug := strings.ToLower(cadena)
	slug = strings.ReplaceAll(slug, " ", "-")
	re := regexp.MustCompile(`[^a-z0-9-]`)
	slug = re.ReplaceAllString(slug, "")
	slug = strings.Trim(slug, "-")
	return slug, nil
}

func cadenaAcortar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	cadena, ok := objeto.(string)
	if !ok {
		return nil, fmt.Errorf("no es una cadena")
	}
	if len(args) < 1 {
		return cadena, nil
	}
	longitud, err := toInt(args[0])
	if err != nil {
		return cadena, nil
	}
	sufijo := "..."
	if len(args) > 1 {
		if s, ok := args[1].(string); ok {
			sufijo = s
		}
	}
	if len(cadena) <= longitud {
		return cadena, nil
	}
	return cadena[:longitud] + sufijo, nil
}

// ============= MÉTODOS PARA DICCIONARIOS =============

func diccObtener(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return nil, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	if val, ok := mapa[clave]; ok {
		return val, nil
	}
	if len(args) > 1 {
		return args[1], nil
	}
	return nil, nil
}

func diccEstablecer(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 2 {
		return nil, fmt.Errorf("establecer requiere clave y valor")
	}
	clave := fmt.Sprintf("%v", args[0])
	mapa[clave] = args[1]
	return nil, nil
}

func diccEliminar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return nil, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	valor, exists := mapa[clave]
	if exists {
		delete(mapa, clave)
	}
	return valor, nil
}

func diccContiene(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return false, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	_, exists := mapa[clave]
	return exists, nil
}

func diccClaves(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	resultado := make([]interface{}, 0, len(mapa))
	for k := range mapa {
		resultado = append(resultado, k)
	}
	return resultado, nil
}

func diccValores(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	resultado := make([]interface{}, 0, len(mapa))
	for _, v := range mapa {
		resultado = append(resultado, v)
	}
	return resultado, nil
}

func diccPares(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	resultado := make([]interface{}, 0, len(mapa))
	for k, v := range mapa {
		resultado = append(resultado, []interface{}{k, v})
	}
	return resultado, nil
}

func diccLongitud(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	return len(mapa), nil
}

func diccVacio(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	return len(mapa) == 0, nil
}

func diccLimpiar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	_, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	return make(map[string]interface{}), nil
}

func diccCopiar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	resultado := make(map[string]interface{})
	for k, v := range mapa {
		resultado[k] = v
	}
	return resultado, nil
}

func diccUnir(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return nil, nil
	}
	if otro, ok := args[0].(map[string]interface{}); ok {
		for k, v := range otro {
			mapa[k] = v
		}
	}
	return nil, nil
}

func diccPop(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return nil, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	valor, exists := mapa[clave]
	if exists {
		delete(mapa, clave)
	}
	return valor, nil
}

func diccTieneClave(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	return diccContiene(objeto, args, kwargs)
}

func diccTieneValor(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return false, nil
	}
	for _, v := range mapa {
		if v == args[0] {
			return true, nil
		}
	}
	return false, nil
}

func diccAListaClaves(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	return diccClaves(objeto, args, kwargs)
}

func diccAListaValores(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	return diccValores(objeto, args, kwargs)
}

func diccDefecto(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 2 {
		return nil, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	if _, exists := mapa[clave]; !exists {
		mapa[clave] = args[1]
	}
	return mapa[clave], nil
}

func diccIncrementar(objeto interface{}, args []interface{}, kwargs map[string]interface{}) (interface{}, error) {
	mapa, ok := objeto.(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("no es un diccionario")
	}
	if len(args) < 1 {
		return nil, nil
	}
	clave := fmt.Sprintf("%v", args[0])
	cantidad := 1.0
	if len(args) > 1 {
		if val, err := toFloat(args[1]); err == nil {
			cantidad = val
		}
	}
	valorActual := 0.0
	if val, ok := mapa[clave]; ok {
		if f, err := toFloat(val); err == nil {
			valorActual = f
		}
	}
	nuevoValor := valorActual + cantidad
	mapa[clave] = nuevoValor
	if nuevoValor == float64(int(nuevoValor)) {
		return int(nuevoValor), nil
	}
	return nuevoValor, nil
}

// ============= REGISTRO DE MÉTODOS =============

var MetodosLista = map[string]MetodoNativo{
	"agregar":         listaAgregar,
	"eliminar":        listaEliminar,
	"eliminar_en":     listaEliminarEn,
	"eliminar_ultimo": listaEliminarUltimo,
	"insertar":        listaInsertar,
	"extender":        listaExtender,
	"contiene":        listaContiene,
	"posicion":        listaPosicion,
	"contar":          listaContar,
	"longitud":        listaLongitud,
	"vacia":           listaVacia,
	"invertir":        listaInvertir,
	"ordenar":         listaOrdenar,
	"ordenar_desc":    listaOrdenarDesc,
	"primero":         listaPrimero,
	"ultimo":          listaUltimo,
	"limpiar":         listaLimpiar,
	"copiar":          listaCopiar,
	"a_texto":         listaATexto,
	"sumar":           listaSumar,
	"maximo":          listaMaximo,
	"minimo":          listaMinimo,
}

var MetodosCadena = map[string]MetodoNativo{
	"longitud":           cadenaLongitud,
	"mayuscula":          cadenaMayuscula,
	"minuscula":          cadenaMinuscula,
	"capitalizar":        cadenaCapitalizar,
	"titulo":             cadenaTitulo,
	"invertir":           cadenaInvertir,
	"contiene":           cadenaContiene,
	"indice":             cadenaIndice,
	"ultimo_indice":      cadenaUltimoIndice,
	"empieza_con":        cadenaEmpiezaCon,
	"termina_con":        cadenaTerminaCon,
	"contar":             cadenaContar,
	"reemplazar":         cadenaReemplazar,
	"unir":               cadenaUnir,
	"dividir":            cadenaDividir,
	"recortar":           cadenaRecortar,
	"recortar_izquierda": cadenaRecortarIzquierda,
	"recortar_derecha":   cadenaRecortarDerecha,
	"extraer":            cadenaExtraer,
	"repetir":            cadenaRepetir,
	"a_entero":           cadenaAEntero,
	"a_decimal":          cadenaADecimal,
	"a_lista":            cadenaALista,
	"es_numero":          cadenaEsNumero,
	"es_digito":          cadenaEsDigito,
	"es_alfabetico":      cadenaEsAlfabetico,
	"es_vacia":           cadenaEsVacia,
	"es_palindromo":      cadenaEsPalindromo,
	"es_mayuscula":       cadenaEsMayuscula,
	"es_minuscula":       cadenaEsMinuscula,
	"a_slug":             cadenaASlug,
	"acortar":            cadenaAcortar,
}

var MetodosDiccionario = map[string]MetodoNativo{
	"obtener":         diccObtener,
	"establecer":      diccEstablecer,
	"eliminar":        diccEliminar,
	"contiene":        diccContiene,
	"claves":          diccClaves,
	"valores":         diccValores,
	"pares":           diccPares,
	"longitud":        diccLongitud,
	"vacio":           diccVacio,
	"limpiar":         diccLimpiar,
	"copiar":          diccCopiar,
	"unir":            diccUnir,
	"sacar":           diccPop,
	"tiene_clave":     diccTieneClave,
	"tiene_valor":     diccTieneValor,
	"a_lista_claves":  diccAListaClaves,
	"a_lista_valores": diccAListaValores,
	"defecto":         diccDefecto,
	"incrementar":     diccIncrementar,
}

// ============= FUNCIONES AUXILIARES =============

func toInt(val interface{}) (int, error) {
	switch v := val.(type) {
	case int:
		return v, nil
	case float64:
		return int(v), nil
	case string:
		return strconv.Atoi(v)
	default:
		return strconv.Atoi(fmt.Sprintf("%v", v))
	}
}

func toFloat(val interface{}) (float64, error) {
	switch v := val.(type) {
	case float64:
		return v, nil
	case int:
		return float64(v), nil
	case string:
		return strconv.ParseFloat(v, 64)
	default:
		return strconv.ParseFloat(fmt.Sprintf("%v", v), 64)
	}
}
