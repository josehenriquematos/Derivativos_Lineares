import requests
import pandas as pd
from pandas.tseries.offsets import BMonthBegin
from workalendar.america import Brazil
from pandas.tseries.offsets import BDay
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt

#Definição de data da curva do DI a ser extraída:
data = "09/01/2025"

#Scrap dos dados da B3:
url = f"https://www2.bmf.com.br/pages/portal/bmfbovespa/lumis/lum-ajustes-do-pregao-ptBR.asp?dData1={data}"
dados_DI = pd.read_html(requests.get(url).text)
tabela = dados_DI[0]

#Extração somente das linhas de ajuste do DI
inicio = tabela[tabela['Mercadoria'] == "DI1 - DI de 1 dia"].index[0]
fim = tabela[tabela['Mercadoria'] == "DOL - Dólar comercial"].index[0]
tabela.loc[inicio:fim, 'Mercadoria'] = tabela.loc[inicio:fim, 'Mercadoria'].fillna("DI1 - DI de 1 dia")
tabela_2 = tabela[tabela['Mercadoria'] == "DI1 - DI de 1 dia"]
tabela_3 = tabela_2.drop(columns = ['Mercadoria', 'Preço de ajuste anterior', 'Variação', 'Valor do ajuste por contrato (R$)'])

#Puxando lista de feriados salva:
with open("feriados_jhenriquematos.txt", "r") as arquivo:
    lista_feriados = [linha.strip() for linha in arquivo]

#Conversão da lista de feriados para o formato datetime
feriados_convertidos = [datetime.strptime(data, "%Y-%m-%d %H:%M:%S") for data in lista_feriados]

#Definição manual da função is_working_day(), para retirar de dias úteis os feriados:
def is_working_day(date, holidays=None):
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    
    # Verifica se é fim de semana
    if date.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
        return False
    
    # Verifica se é feriado, se uma lista de feriados for fornecida
    if holidays and date in holidays:
        return False
    
    return True
    
#Dataframes de datas para os contratos de DI
def datas_DI(valor):
    # Mapeamento da primeira letra para o número do mês
    meses_aux = {
    'F': 1,
    'G': 2,
    'H': 3, 
    'J': 4,
    'K': 5, 
    'M': 6, 
    'N': 7, 
    'Q': 8, 
    'U': 9, 
    'V': 10, 
    'X': 11, 
    'Z': 12
    }

    anos_aux = {
    '23': 2023, 
    '24': 2024, 
    '25': 2025, 
    '26': 2026, 
    '27': 2027, 
    '28': 2028, 
    '29': 2029, 
    '30': 2030, 
    '31': 2031, 
    '32': 2032, 
    '33': 2033, 
    '34': 2034, 
    '35': 2035, 
    '36': 2036, 
    '37': 2037, 
    '38': 2038, 
    '39': 2039, 
    '40': 2040, 
    '41': 2041, 
    '42': 2042, 
    '43': 2043, 
    '44': 2044, 
    '45': 2045
    }

    primeira_letra = valor[0].upper()
    ultimos_numeros = valor[1:]

    # Obter o mês e o ano correspondentes
    mes = meses_aux.get(primeira_letra)
    ano = anos_aux.get(ultimos_numeros)

    if mes and ano:
        # Calcular o primeiro dia útil do mês e ano
        primeiro_dia_util = pd.Timestamp(f'{ano}-{mes:02d}-01')
        # Verificar se a data inicial é um dia útil e não é feriado
        while not is_working_day(primeiro_dia_util, holidays=feriados_convertidos):
            primeiro_dia_util += BDay(1)  # Avançar para o próximo dia útil
        return primeiro_dia_util.date()
    else:
        return None  # Retorna None se algo estiver errado

tabela_3 = tabela_3.rename(columns={"Vencimento": "Eventos", "Preço de ajuste Atual": "PU de Ajuste"})
tabela_3["Datas"] = tabela_3['Eventos'].apply(datas_DI)

#Nova ordem: Datas primeiro, seguido das outras colunas
coluna_destaque = "Datas"
outras_colunas = [col for col in tabela_3.columns if col != coluna_destaque]
nova_ordem = [coluna_destaque] + outras_colunas
tabela_3 = tabela_3[nova_ordem]

#Definindo datas do Copom:
datas_copom = pd.DataFrame({
    "Datas": pd.to_datetime([
        "29-01-2025",
        "19-03-2025",
        "07-05-2025",
        "18-06-2025",
        "30-07-2025",
        "17-09-2025",
        "05-11-2025",
        "10-12-2025"
    ], dayfirst=True)
})

#Inserindo datas do Copom no DataFrame
tabela_4 = pd.concat([tabela_3, datas_copom], ignore_index=True)
tabela_4["Datas"] = pd.to_datetime(tabela_4["Datas"], dayfirst=True)
tabela_5 = tabela_4.fillna({"Eventos": "Copom"})

#Cálculo de NDU:
data_fixa = pd.to_datetime(data, dayfirst=True)

#Definindo as funções get_working_days_delta e calcular_dias_uteis, que vai efetivamente calcular os NDU:
def get_working_days_delta(start_date, end_date, holidays=None):
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)
    all_dates = pd.date_range(start=start_date, end=end_date)
    working_days = [date for date in all_dates if date.weekday() < 5]
    if holidays:
        holidays = pd.to_datetime(holidays)
        working_days = [day for day in working_days if day not in holidays]
    return len(working_days)

def calcular_dias_uteis(data_fixa, data_referencia):
    # Converter as datas para o formato correto
    data_fixa = pd.to_datetime(data_fixa, dayfirst=True)
    data_referencia = pd.to_datetime(data_referencia, dayfirst=True)
    # Lista de dias úteis entre as duas datas
    dias_uteis = get_working_days_delta(data_fixa, data_referencia, holidays=feriados_convertidos)-1
    return dias_uteis

# Aplicar a função ao DataFrame
tabela_5['NDU'] = tabela_5['Datas'].apply(lambda data_referencia: calcular_dias_uteis(data_fixa, data_referencia))

#Definição de taxa de fechamento a partir do ajuste de fechamento:
tabela_5['PU de Ajuste'] = tabela_5['PU de Ajuste'].str.replace('.', '', regex=True)  # Remove pontos (milhares)
tabela_5['PU de Ajuste'] = tabela_5['PU de Ajuste'].str.replace(',', '.', regex=True)  # Substitui vírgula por ponto
tabela_5['PU de Ajuste'] = pd.to_numeric(tabela_5['PU de Ajuste'])
tabela_5["Taxa de fechamento"] = tabela_5.apply(lambda row: (pow((100000/row["PU de Ajuste"]),(252/row["NDU"])) - 1)*100, axis = 1)
tabela_5 = tabela_5.drop(columns=["PU de Ajuste"])

#Definição da Taxa Selic Over e inserção na curva:
taxa_selic_over = 12.15
tabela_5.loc[len(tabela_5)] = [data_fixa, "Selic Over Hoje", 1, taxa_selic_over]
tabela_5 = tabela_5.reset_index(drop=False)
tabela_5 = tabela_5.drop(columns=["index"])
tabela_5.sort_values(by="Datas", ascending = True, inplace = True)
tabela_5 = tabela_5.reset_index(drop=False)
tabela_5 = tabela_5.drop(columns=["index"])

#Calculando a taxa interpolada nos dias de Copom
tabela_5["Taxa de fechamento"] = tabela_5["Taxa de fechamento"].fillna(0)
indices_interpolacao = tabela_5.index[tabela_5["Taxa de fechamento"].eq(0)].tolist()

#Função para calcular a taxa interpolada nos dias de reunião do Copom. A interpolação usada foi a Flat Forward 252
def taxa_interpolada(dataframe, indices, coluna):
    for indices_interpolados in indices:
        taxa = (pow(pow((1 + tabela_5.loc[indices_interpolados - 1, "Taxa de fechamento"]/100),(tabela_5.loc[indices_interpolados - 1, "NDU"]/252))*pow(pow((1+tabela_5.loc[indices_interpolados + 1, "Taxa de fechamento"]/100),(tabela_5.loc[indices_interpolados + 1, "NDU"]/252))/pow((1+tabela_5.loc[indices_interpolados - 1, "Taxa de fechamento"]/100),(tabela_5.loc[indices_interpolados - 1, "NDU"]/252)),((tabela_5.loc[indices_interpolados, "NDU"]-tabela_5.loc[indices_interpolados - 1, "NDU"])/(tabela_5.loc[indices_interpolados + 1, "NDU"]-tabela_5.loc[indices_interpolados - 1, "NDU"]))),(252/tabela_5.loc[indices_interpolados, "NDU"]))-1)*100
        dataframe.loc[indices_interpolados, coluna] = taxa
    return dataframe

tabela_5 = taxa_interpolada(tabela_5, indices_interpolacao, "Taxa de fechamento")
tabela_5 = tabela_5.sort_values(by="Datas").reset_index(drop=True)

#Definição das taxas a termo da curva:
def taxa_termo(linha):
    if linha.name == 0:
        return taxa_selic_over
    return (pow(pow((1+tabela_5.loc[linha.name, "Taxa de fechamento"]/100),(tabela_5.loc[linha.name, "NDU"]/252))/pow((1+tabela_5.loc[linha.name - 1, "Taxa de fechamento"]/100),(tabela_5.loc[linha.name - 1, "NDU"]/252)),(252/(tabela_5.loc[linha.name, "NDU"] - tabela_5.loc[linha.name - 1, "NDU"]))) - 1)*100

tabela_5["Taxa termo"] = tabela_5.apply(taxa_termo, axis=1)

#Calculo da variação da taxa a termo em cada trecho da curva
def variacao_termo(linha):
    if linha.name == 0:
        return 0
    return round((tabela_5.loc[linha.name, "Taxa termo"] - tabela_5.loc[linha.name - 1, "Taxa termo"])*100,2)

tabela_5["Variacao termo"] = tabela_5.apply(variacao_termo, axis=1)
 
#Criacao da precificacao consolidada por reuniao do Copom:

#Criar grupos com base nas linhas onde "Copom" aparece
tabela_5['Grupo'] = (tabela_5['Eventos'] == 'Copom').cumsum()

# Calcular a soma somente entre as linhas dentro de cada grupo
tabela_5['Precificacao Copom'] = tabela_5.groupby('Grupo')['Variacao termo'].transform('sum')

#Criação de dashboard para CDIE
bps_copom = tabela_5.loc[tabela_5['Eventos'] == "Copom", "Precificacao Copom"].tolist()
bps_copom.pop(-1)
ultimo_copom_index = tabela_5[tabela_5["Eventos"] == "Copom"].index[-1]
ultimo_copom = tabela_5.loc[ultimo_copom_index, "Variacao termo"].tolist()
bps_copom.extend([ultimo_copom])
datas_copom_lista = tabela_5.loc[tabela_5['Eventos'] == "Copom", "Datas"].tolist()
datas_copom_lista_formatada = [data.strftime("%b-%Y") for data in datas_copom_lista]

#Criação a partir de um gráfico de barras
fig, ax = plt.subplots()

x = np.arange(len(datas_copom_lista_formatada))
ax.bar(x, bps_copom, width=0.8, align='center', color='black')    
plt.xticks(x, datas_copom_lista_formatada, fontsize=7.5)
plt.yticks(np.arange(0, max(bps_copom) + 25, 25))
ax = plt.gca()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
#Adicionar título principal
plt.suptitle('CDIE', fontsize=16, fontweight='light', fontfamily='rockwell', x=0.135, y=0.9)

#Adicionar subtítulo
plt.title(f'COPOM Market Expectations, bps - Last: {data_fixa:%d-%m-%Y}', fontsize=12, fontweight='light', fontfamily='rockwell', x=0.36, y=1.05)

#Ajustar layout para evitar sobreposição
plt.tight_layout(rect=[0, 0, 1, 0.95])
ax.legend()

plt.show()