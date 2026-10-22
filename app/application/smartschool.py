from app import app
from zeep import Client
import inspect

#logging on file level
import logging, sys
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

SMARTSCHOOL_ERROR_MESSAGES = {
    "1": "De naam dient minimaal uit 2 karakters te bestaan.",
    "10": "Er is een fout gebeurd tijdens het verwerken van de gegevens. Er is niets toegepast.",
    "11": "Er is een fout opgetreden tijdens het bewaren van de klasgegevens.",
    "12": "Deze gebruiker bestaat niet",
    "13": "Er is een fout opgetreden tijdens het kopiëren/verplaatsen van de gebruikers naar de opgegeven klas.",
    "14": "Onvoldoende gegeven aangeleverd.",
    "15": "Dubbele gebruikersnaam",
    "16": "Dubbele interne nummer",
    "17": "Er is een fout opgetreden tijdens het bewaren van één of meerdere profielvelden.",
    "18": "Er is een fout opgetreden bij het versturen van het bericht",
    "19": "Parent-ID bestaat niet !",
    "2": "De voornaam dient uit minimaal 2 karakters te bestaan.",
    "20": "Cursus toevoegen mislukt.",
    "21": "Cursus met zelfde naam aanwezig.",
    "22": "Cursus niet gevonden.",
    "23": "Er is een onbekende fout opgetreden tijdens de verwerking.",
    "24": "Er is reeds een gebruiker aanwezig met dit intern nummer. Gelieve een ander nummer in te geven.",
    "25": "Opgelet, de gebruiker kon niet worden gewijzigd, omdat deze niet bestaat in Smartschool.",
    "26": "Opgelet, de gebruiker kon niet worden toegevoegd, omdat deze reeds bestaat in Smartschool.",
    "27": "Opgelet, het instellingsnummer komt niet voor in Smartschool. Gelieve eerst de instelling toe te voegen.",
    "28": "Het selecteren van een basisrol is verplicht.",
    "29": "U mag de basisrol van deze account niet meer wijzigen.",
    "3": "De gebruikersnaam dient minimaal uit 2 karakters bestaan.",
    "30": "Enkel leerlingen (basisrol leerling) mogen lid zijn van officiële klassen.",
    "31": "De leerling mag maar lid zijn van één officiële klas.",
    "32": "Een leerling dient lid te zijn van één officiële klas.",
    "33": "Het registeren van de klasbeweging is mislukt.",
    "34": "De leerling kan niet geactiveerd worden omdat hij geen lid is van een officiële klas.",
    "35": "Het instellingsnummer is verplicht bij een officiële klas.",
    "36": "U mag het type van een officiële klas niet wijzigen.",
    "37": "U mag het type van deze klas of groep niet wijzigen omdat sommige leden van deze groep of klas niet de basisrol leerling hebben.",
    "38": "U mag het type van deze klas of groep niet wijzigen omdat sommige leden van deze groep of klas reeds lid zijn van een andere officiële klas.",
    "39": "U dient een vormingscomponent te selecteren.",
    "4": "Het nieuwe wachtwoord is niet complex genoeg.<br>Bekijk de voorwaarden voor een wachtwoord of wachtzin in de handleiding (Profiel > Gebruikersnaam en wachtwoord).",
    "40": "U mag de naam van een klas niet meer wijzigen.",
    "41": "U mag het administratiefnummer niet meer wijzigen.",
    "42": "U mag het instellingsnummer niet meer wijzigen.",
    "43": "U mag de vormingscomponent niet meer wijzigen.",
    "44": "De vormingscomponent is verplicht op te geven.",
    "45": "U mag het type van een klas niet wijzigen.",
    "46": "U dient het type van de groep te selecteren.",
    "47": "Er bestaat reeds een klas met dezelfde unieke klas- of groepcode",
    "48": "Het intern nummer bestaat reeds.",
    "49": "De datum is niet geldig",
    "5": "Er is geen groep geselecteerd.",
    "50": "De module ",
    "Skore": " is niet geactiveerd",
    "51": "Er is een fout opgetreden tijdens het uitschrijven van de leerling",
    "52": "Dit wachtwoord werd niet toegestaan. Gelieve een ander wachtwoord te kiezen.",
    "53": "De bovenliggende groep werd niet gevonden.",
    "54": "De bovenliggende groep mag geen officiële klas zijn.",
    "55": "Een officiële klas kan geen subgroepen bevatten.",
    "56": "Gelieve een geldige datum op te geven voor het schooljaar",
    "57": "De ",
    "Roostercode": " dient uniek te zijn. De waarde die u invulde is reeds in gebruik.",
    "6": "De gebruikersnaam bestaat reeds.",
    "7": "De wachtwoorden zijn niet identiek.",
    "8": "Het opgegeven webserviceswachtwoord is niet correct.",
    "9": "Deze gebruiker bestaat niet"
}

soap = Client(app.config["SS_API_URL"])

def send_message(to, sender, subject, body, account=0, enable_sending=True):
    try:
        ret = -1
        if enable_sending:
            ret = soap.service.sendMsg(app.config["SS_API_KEY"], to, subject, body, sender, "", account, False)
        log.info(f'{inspect.currentframe().f_code.co_name}: to {to}/{account}, from {sender}, subject {subject}, ret {ret}, enable_sending {enable_sending}')
        if ret != 0:
            log.error(f'{inspect.currentframe().f_code.co_name}: Error sending message: {SMARTSCHOOL_ERROR_MESSAGES.get(str(ret), "Error message not found")}')
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return -1
