from saddogs_scrape.spiders.base.aspnet_ajax_spider import AspNetAjaxCountSpider
from saddogs_scrape.spiders.base.count_spider import CountSpider


class GranCanariaBanaderos(AspNetAjaxCountSpider):
    name = "gran_canaria_banaderos"

    rescue_name = "Banaderos"
    island = "Gran Canaria"

    start_urls = ["https://albergueanimalesgrancanaria.com/Nuestros-Animales"]


class GranCanariaTelde(AspNetAjaxCountSpider):
    name = "gran_canaria_telde"

    rescue_name = "Telde"
    island = "Gran Canaria"

    start_urls = ["https://albergueanimalestelde.com/Nuestros-Animales"]


class GranCanariaSosHunde(CountSpider):
    name = "gran_canaria_sos_hunde"

    rescue_name = "SOS Hunde"
    island = "Gran Canaria"

    start_urls = ["https://www.sos-hunde-gc.com/vermittlung"]

    selector = 'div[role="listitem"]._FiCX'


class GranCanariaAda(CountSpider):
    name = "gran_canaria_ada"

    rescue_name = "ADA Gran Canaria"
    island = "Gran Canaria"

    start_urls = ["https://www.adagrancanaria.org/pet-category/perros/"]

    selector = "div.item:not(.item_placeholder)"
    pagination_selector = "a.next.page-numbers::attr(href)"
