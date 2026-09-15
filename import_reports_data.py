import os
import django
from datetime import date, time

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'guestranchmanagementplatform.settings')
django.setup()

from django.db import transaction
from apps.cabins.models import Cabin
from apps.clients.models import Client, Household, HouseholdMember
from apps.reservations.models import Reservation, ReservationCabin, ReservationGuest

CABINS_DATA = [
    {"name": "Honeymoon", "capacity": 2, "sort_order": 1},
    {"name": "Ranger", "capacity": 2, "sort_order": 2},
    {"name": "Little Sourdough", "capacity": 2, "sort_order": 3},
    {"name": "Little Squaw", "capacity": 2, "sort_order": 4},
    {"name": "Big Sourdough", "capacity": 4, "sort_order": 5},
    {"name": "Black Powder", "capacity": 4, "sort_order": 6},
    {"name": "Bear Paw", "capacity": 4, "sort_order": 7},
    {"name": "Silver Dollar", "capacity": 2, "sort_order": 8},
    {"name": "Tensleep", "capacity": 4, "sort_order": 9},
    {"name": "Shoshone", "capacity": 4, "sort_order": 10},
    {"name": "Bigfoot", "capacity": 4, "sort_order": 11},
    {"name": "Wagon Wheel", "capacity": 4, "sort_order": 12},
    {"name": "Virginian", "capacity": 4, "sort_order": 13},
    {"name": "Trapper", "capacity": 4, "sort_order": 14},
    {"name": "Wapiti", "capacity": 4, "sort_order": 15},
    {"name": "Timberline", "capacity": 8, "sort_order": 16},
    {"name": "Ram's Head", "capacity": 8, "sort_order": 17},
    {"name": "Eagle's Nest", "capacity": 4, "sort_order": 18},
]

DATA_WEEK1 = [
    {
        "cabin": "Honeymoon",
        "household": {
            "name": "Brad & Connie Holzworth",
            "address_line_1": "7648 Red Bay Court",
            "city": "Dublin", "state": "OH", "postal_code": "43016",
            "phone": "614-571-4251", "email": "bradleyholzworth@gmail.com"
        },
        "guests": [
            {
                "first_name": "Brad", "last_name": "Holzworth",
                "phone": "614-571-4251", "email": "bradleyholzworth@gmail.com",
                "notes": "3rd year at Paradise\nDriving"
            },
            {
                "first_name": "Connie", "last_name": "Holzworth",
                "phone": "614-571-4251", "email": "bradleyholzworth@gmail.com",
                "food_requests": "Connie does not eat beef",
                "notes": "3rd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Ranger",
        "household": {
            "name": "Pat Leonard",
            "address_line_1": "356 McCorrie Ln.",
            "city": "Portsmouth", "state": "RI", "postal_code": "02871",
            "phone": "703-819-9818", "email": "palesq@aol.com"
        },
        "guests": [
            {
                "first_name": "Pat", "last_name": "Leonard",
                "phone": "703-819-9818", "email": "palesq@aol.com",
                "notes": "18th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Little Sourdough",
        "household": {
            "name": "Marty & Sharon Potter",
            "address_line_1": "609 Moon Shell Circle",
            "city": "New Smyrna Beach", "state": "FL", "postal_code": "32168",
            "phone": "407-361-4909", "email": "martypotter@gmail.com"
        },
        "guests": [
            {
                "first_name": "Marty", "last_name": "Potter",
                "phone": "407-361-4909", "email": "martypotter@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            },
            {
                "first_name": "Sharon", "last_name": "Potter",
                "phone": "407-361-4909", "email": "martypotter@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Little Squaw",
        "household": {
            "name": "Kris Hanson & Dondi Schwartz",
            "address_line_1": "1191 Niles Ave.",
            "city": "St. Paul", "state": "MN", "postal_code": "55116",
            "phone": "651-315-1808", "email": "hansonkris1@gmail.com"
        },
        "guests": [
            {
                "first_name": "Kris", "last_name": "Hanson",
                "phone": "651-315-1808", "email": "hansonkris1@gmail.com",
                "notes": "2nd year at Paradise\nDriving"
            },
            {
                "first_name": "Dondi", "last_name": "Schwartz",
                "phone": "651-315-1808", "email": "hansonkris1@gmail.com",
                "notes": "2nd year at Paradise\nDondi birthday 9/1\nDriving"
            }
        ]
    },
    {
        "cabin": "Big Sourdough",
        "household": {
            "name": "Heith & Barbara Heitkamp",
            "address_line_1": "425 Prairie Way South",
            "city": "Bayport", "state": "MN", "postal_code": "55003",
            "phone": "360-910-7161", "email": "heithheitkamp@gmail.com"
        },
        "guests": [
            {
                "first_name": "Heith", "last_name": "Heitkamp",
                "phone": "360-910-7161", "email": "heithheitkamp@gmail.com",
                "notes": "1st year at Paradise\nFriends of Kris Hanson & Dondi Schwartz\nDriving"
            },
            {
                "first_name": "Barbara", "last_name": "Heitkamp",
                "phone": "360-910-7161", "email": "heithheitkamp@gmail.com",
                "notes": "1st year at Paradise\nFriends of Kris Hanson & Dondi Schwartz\nDriving"
            }
        ]
    },
    {
        "cabin": "Black Powder",
        "household": {
            "name": "James Bennett & Sylvie Peterson",
            "address_line_1": "405 NW 131st St.",
            "city": "Vancouver", "state": "WA", "postal_code": "98685",
            "phone": "503-444-1187", "email": "j_e_bennett@yahoo.com"
        },
        "guests": [
            {
                "first_name": "James", "last_name": "Bennett",
                "phone": "503-444-1187", "email": "j_e_bennett@yahoo.com",
                "notes": "5th year at Paradise\nDriving"
            },
            {
                "first_name": "Sylvie", "last_name": "Peterson",
                "phone": "503-444-1187", "email": "j_e_bennett@yahoo.com",
                "allergies": "Dairy sensitive",
                "food_requests": "Sylvie is dairy sensitive and no seafood or fish",
                "notes": "5th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Bear Paw",
        "household": {
            "name": "Karee Valek",
            "address_line_1": "5321 Gulf of Mexico Drive",
            "address_line_2": "Unit 4",
            "city": "Longboat Key", "state": "FL", "postal_code": "34228",
            "phone": "941-376-6046", "email": "kjvalek@gmail.com"
        },
        "guests": [
            {
                "first_name": "Karee", "last_name": "Valek",
                "phone": "941-376-6046", "email": "kjvalek@gmail.com",
                "notes": "2nd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Bear Paw",
        "household": {
            "name": "Beth Wheeler",
            "address_line_1": "5350 Perrier Street",
            "city": "New Orleans", "state": "LA", "postal_code": "70115",
            "phone": "504-858-0117", "email": "ewheeler@liskow.com"
        },
        "guests": [
            {
                "first_name": "Beth", "last_name": "Wheeler",
                "phone": "504-858-0117", "email": "ewheeler@liskow.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Silver Dollar",
        "household": {
            "name": "Diane Esarey",
            "address_line_1": "634 West 21st Apt. #1",
            "city": "San Pedro", "state": "CA", "postal_code": "90731",
            "phone": "310-514-7580", "email": "marronediane@hotmail.com"
        },
        "guests": [
            {
                "first_name": "Diane", "last_name": "Esarey",
                "phone": "310-514-7580", "email": "marronediane@hotmail.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan UA5127 1:41pm\nSheridan UA5079 2:21pm"
            }
        ]
    },
    {
        "cabin": "Tensleep",
        "household": {
            "name": "Sara Martineau",
            "address_line_1": "90 Mott Street Apt. 1",
            "city": "New Bedford", "state": "MA", "postal_code": "02744",
            "phone": "508-264-8501", "email": "askm98@verizon.net"
        },
        "guests": [
            {
                "first_name": "Sara", "last_name": "Martineau",
                "phone": "508-264-8501", "email": "askm98@verizon.net",
                "notes": "2nd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Tensleep",
        "household": {
            "name": "Linda Carbone",
            "address_line_1": "50 Oak Street",
            "city": "Plympton", "state": "MA", "postal_code": "02367",
            "phone": "781-789-7499", "email": "ridefieldstone@also.com"
        },
        "guests": [
            {
                "first_name": "Linda", "last_name": "Carbone",
                "phone": "781-789-7499", "email": "ridefieldstone@also.com",
                "notes": "2nd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Shoshone",
        "household": {
            "name": "Tom & Nancy Kenney",
            "address_line_1": "411 Arbutus Pl.",
            "city": "Bellingham", "state": "WA", "postal_code": "98225",
            "phone": "360-961-1223", "email": "kenney411@comcast.net"
        },
        "guests": [
            {
                "first_name": "Tom", "last_name": "Kenney",
                "phone": "360-961-1223", "email": "kenney411@comcast.net",
                "notes": "25th year at Paradise\nInviting Tom’s cousin (Linda & Dan) to a Pavillion meal\nWants tea kettle, electric fan, & 4 stemless wine glasses, 2 Paradise mugs in cabin\nBoxes in the office\nWants help unloading and loading the car\nDriving"
            },
            {
                "first_name": "Nancy", "last_name": "Kenney",
                "phone": "360-303-2006", "email": "kenney411@comcast.net",
                "medical_notes": "Nancy had total shoulder replacement in May",
                "notes": "25th year at Paradise\nInviting Tom’s cousin (Linda & Dan) to a Pavillion meal\nWants tea kettle, electric fan, & 4 stemless wine glasses, 2 Paradise mugs in cabin\nBoxes in the office\nWants help unloading and loading the car\nNancy had total shoulder replacement in May\nDriving"
            }
        ]
    },
    {
        "cabin": "Bigfoot",
        "household": {
            "name": "Debby Douglass",
            "address_line_1": "716 Wortham Drive",
            "city": "Grapevine", "state": "TX", "postal_code": "76051",
            "phone": "214-215-3121", "email": "debra.douglass@verizon.net"
        },
        "guests": [
            {
                "first_name": "Debby", "last_name": "Douglass",
                "phone": "214-215-3121", "email": "debra.douglass@verizon.net",
                "notes": "15th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Bigfoot",
        "household": {
            "name": "Jane Moore",
            "address_line_1": "32300 Wakeman Shores Drive",
            "city": "Grand Rapids", "state": "MN", "postal_code": "55744",
            "phone": "563-580-5253", "email": "kaamsr1957@gmail.com"
        },
        "guests": [
            {
                "first_name": "Jane", "last_name": "Moore",
                "phone": "563-580-5253", "email": "kaamsr1957@gmail.com",
                "notes": "14th year at Paradise\nWants nicer thinner, lipped coffee mugs\nWants some stemless wine glasses\nDriving"
            }
        ]
    },
    {
        "cabin": "Wagon Wheel",
        "household": {
            "name": "Josh Clydesdale & Megan Tennant",
            "address_line_1": "23 Brookfield Gardens",
            "city": "Ahaghill, Ballymena", "state": "BT42 ILH", "postal_code": "", "country": "UK",
            "phone": "07985465165", "email": "jclydesdale96@gmail.com"
        },
        "guests": [
            {
                "first_name": "Josh", "last_name": "Clydesdale",
                "phone": "07985465165", "email": "jclydesdale96@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            },
            {
                "first_name": "Megan", "last_name": "Tennant",
                "phone": "07734088411", "email": "floralmeganx@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Virginian",
        "household": {
            "name": "Samantha Barrell",
            "address_line_1": "Willow Farm, Thorpe Row Shipdham Thetford",
            "city": "Norfolk", "state": "IP25 7NN", "postal_code": "", "country": "UK",
            "phone": "+447770667715", "email": "samantha.barrell@hotmail.com"
        },
        "guests": [
            {
                "first_name": "Sam (Samantha)", "last_name": "Barrell",
                "phone": "+447770667715", "email": "samantha.barrell@hotmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Virginian",
        "household": {
            "name": "Sophie Britch",
            "address_line_1": "Ringland Lodge, Field Road",
            "city": "Ringland", "state": "NR8 6RH", "postal_code": "", "country": "UK",
            "phone": "+07951015846", "email": "blythgreen@hotmail.com"
        },
        "guests": [
            {
                "first_name": "Sophie", "last_name": "Britch",
                "phone": "+07951015846", "email": "blythgreen@hotmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Virginian",
        "household": {
            "name": "Penny Mackey",
            "address_line_1": "6 Symphony Gardens, Attleborough",
            "city": "Norfolk", "state": "NR17 1GD", "postal_code": "", "country": "UK",
            "phone": "", "email": "pap6070@yahoo.co.uk"
        },
        "guests": [
            {
                "first_name": "Penny", "last_name": "Mackey",
                "phone": "", "email": "pap6070@yahoo.co.uk",
                "notes": "3rd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Trapper",
        "household": {
            "name": "Shelly Rabe",
            "address_line_1": "32395 Leelane",
            "city": "Farmington", "state": "MI", "postal_code": "48336",
            "phone": "248-417-1030", "email": "ser1959@aol.com"
        },
        "guests": [
            {
                "first_name": "Shelly", "last_name": "Rabe",
                "phone": "248-417-1030", "email": "ser1959@aol.com",
                "notes": "1st year at Paradise\nShuttle\nGillette UA4750 @ 12:42pm\nGillette UA5682 @ 1:19pm"
            }
        ]
    },
    {
        "cabin": "Trapper",
        "household": {
            "name": "Gail Briney",
            "address_line_1": "18421 Wakenden",
            "city": "Redford", "state": "MI", "postal_code": "48240",
            "phone": "734-788-9959", "email": "kgbriney@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Gail", "last_name": "Briney",
                "phone": "734-788-9959", "email": "kgbriney@yahoo.com",
                "notes": "1st year at Paradise\nShuttle\nGillette UA4750 @ 12:42pm\nGillette UA5682 @ 1:19pm"
            }
        ]
    },
    {
        "cabin": "Wapiti",
        "household": {
            "name": "Cherie Hill",
            "address_line_1": "53 Skagit Key",
            "city": "Bellevue", "state": "WA", "postal_code": "98006",
            "phone": "425-445-8615", "email": "crhill4@msn.com"
        },
        "guests": [
            {
                "first_name": "Cherie", "last_name": "Hill",
                "phone": "425-445-8615", "email": "crhill4@msn.com",
                "food_requests": "No seafood",
                "medical_notes": "May be affected by altitude - not serious",
                "notes": "1st year at Paradise\nJackie is daughter-in-law\nNo seafood\nBirthday is 9/4\nMay be affected by altitude - not serious\nShuttle Requested\nGillette UA4750 @ 12:51pm\nGillette UA5682 @ 1:26 pm"
            }
        ]
    },
    {
        "cabin": "Wapiti",
        "household": {
            "name": "Jackie Hill",
            "address_line_1": "PO Box 3189",
            "city": "Chelan", "state": "WA", "postal_code": "98816",
            "phone": "360-982-1224", "email": "jackie_hill23@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Jackie", "last_name": "Hill",
                "phone": "360-982-1224", "email": "jackie_hill23@yahoo.com",
                "notes": "1st year at Paradise\nCherie is mother-in-law\n38th Birthday is 9/2\nShuttle Requested\nGillette UA4750 @ 12:51pm\nGillette UA5682 @ 1:26 pm"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Dillon & Sheree Smith",
            "address_line_1": "11136 Lands End Lane",
            "city": "Jacksonville", "state": "FL", "postal_code": "32225",
            "phone": "401-418-1054", "email": "sdaniellemc6@aol.com"
        },
        "guests": [
            {
                "first_name": "Dillon", "last_name": "Smith",
                "phone": "401-418-1054", "email": "dismith5421@gmail.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\nDriving"
            },
            {
                "first_name": "Sheree", "last_name": "Smith",
                "phone": "401-418-1054", "email": "sdaniellemc6@aol.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Kimberly Leonard",
            "address_line_1": "41 A Rockland St",
            "city": "Holliston", "state": "MA", "postal_code": "01746",
            "phone": "774-573-2128", "email": "kimberly.leonard1@gmail.com"
        },
        "guests": [
            {
                "first_name": "Kimberly", "last_name": "Leonard",
                "phone": "774-573-2128", "email": "kimberly.leonard1@gmail.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Mary Appelman",
            "address_line_1": "35 E 9th Street",
            "city": "Newport", "state": "KY", "postal_code": "41071",
            "phone": "", "email": "mary.appelman@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Mary", "last_name": "Appelman",
                "phone": "", "email": "mary.appelman@yahoo.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Riley Smith",
            "address_line_1": "818 19th Ave South Apt. 1607",
            "city": "Nashville", "state": "TN", "postal_code": "37203",
            "phone": "401-447-4396", "email": "rasmith3@hotmail.com"
        },
        "guests": [
            {
                "first_name": "Riley", "last_name": "Smith",
                "phone": "401-447-4396", "email": "rasmith3@hotmail.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\n9/5 31st Birthday\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Michael Caniff",
            "address_line_1": "2936 Almond Street",
            "city": "Philadelphia", "state": "PA", "postal_code": "19134",
            "phone": "339-227-0060", "email": "mike.caniff@gmail.com"
        },
        "guests": [
            {
                "first_name": "Michael", "last_name": "Caniff",
                "phone": "339-227-0060", "email": "mike.caniff@gmail.com",
                "notes": "1st year at Paradise\nRelated to Pat Leonard\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Brenda Metzger",
            "address_line_1": "1945 Tobiano Circle",
            "city": "Heber City", "state": "UT", "postal_code": "84032",
            "phone": "650-450-1139", "email": "brenda@kbhorses.com"
        },
        "guests": [
            {
                "first_name": "Brenda", "last_name": "Metzger",
                "phone": "650-450-1139", "email": "brenda@kbhorses.com",
                "notes": "1st year at Paradise\nDriving"
            },
            {
                "first_name": "Laura", "last_name": "Seemann",
                "phone": "650-450-1139", "email": "brenda@kbhorses.com",
                "notes": "1st year at Paradise\nBrenda’s daughter\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Nancy Lynch",
            "address_line_1": "8549 SE 71st Ave",
            "city": "Ocala", "state": "FL", "postal_code": "34472",
            "phone": "352-804-5026", "email": "nancylynch007@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Nancy", "last_name": "Lynch",
                "phone": "352-804-5026", "email": "nancylynch007@yahoo.com",
                "notes": "1st year at Paradise\nNancy Lynch - did not come\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Donis Bankhead",
            "address_line_1": "6105 Crimson Drive",
            "city": "McKinney", "state": "TX", "postal_code": "75072",
            "phone": "214-505-6730", "email": "donisb17@gmail.com"
        },
        "guests": [
            {
                "first_name": "Donis", "last_name": "Bankhead",
                "phone": "214-505-6730", "email": "donisb17@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Nancy Gray",
            "address_line_1": "8935 SE 168th Tailfer St",
            "city": "The Villages", "state": "FL", "postal_code": "32162",
            "phone": "801-634-8056", "email": "graybearutah@gmail.com"
        },
        "guests": [
            {
                "first_name": "Nancy", "last_name": "Gray",
                "phone": "801-634-8056", "email": "graybearutah@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Victoria Redel",
            "address_line_1": "90 Riverside Dr. Apt 12A",
            "city": "New York City", "state": "NY", "postal_code": "10024",
            "phone": "917-488-1777", "email": "victoraiaredel@gmail.com"
        },
        "guests": [
            {
                "first_name": "Victoria", "last_name": "Redel",
                "phone": "917-488-1777", "email": "victoraiaredel@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Carrie Russell",
            "address_line_1": "1925 Tobiano Circle",
            "city": "Heber City", "state": "UT", "postal_code": "84032",
            "phone": "703-965-8873", "email": "carrie@kbhorses.com"
        },
        "guests": [
            {
                "first_name": "Carrie", "last_name": "Russell",
                "phone": "703-965-8873", "email": "carrie@kbhorses.com",
                "allergies": "No dairy, no cheese",
                "food_requests": "No dairy\nNo cheese\nNo fried food",
                "notes": "1st year at Paradise\nNo dairy\nNo cheese\nNo fried food\nDriving"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Bonnie Abate",
            "address_line_1": "8669 Marmot Circle",
            "city": "Park City", "state": "UT", "postal_code": "84098",
            "phone": "949-370-9120", "email": "bonnieabate@gmail.com"
        },
        "guests": [
            {
                "first_name": "Bonnie", "last_name": "Abate",
                "phone": "949-370-9120", "email": "bonnieabate@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Eagle's Nest",
        "household": {
            "name": "Janet Brown & Lynn Richardson",
            "address_line_1": "PO Box 480",
            "city": "Coulterville", "state": "CA", "postal_code": "95311",
            "phone": "209-878-3691", "email": "dana_brown@msn.com"
        },
        "guests": [
            {
                "first_name": "Janet", "last_name": "Brown",
                "phone": "209-878-3691", "email": "dana_brown@msn.com",
                "food_requests": "Vegetarian",
                "notes": "4th year at Paradise\nLynn is her sister\nVegetarian\nShuttle\nSheridan UA5127 @ 1:41pm\nNothing listed for outbound"
            },
            {
                "first_name": "Lynn", "last_name": "Richardson",
                "phone": "707-484-9353", "email": "dana_brown@msn.com",
                "allergies": "Highly allergic to nuts",
                "food_requests": "Vegetarian",
                "notes": "4th year at Paradise\nJanet is her sister\nVegetarian\nHighly allergic to nuts\nShuttle\nSheridan UA5127 @ 1:41pm\nNothing listed for outbound"
            }
        ]
    }
]

DATA_WEEK2 = [
    {
        "cabin": "Honeymoon",
        "household": {
            "name": "Donna Lieberson",
            "address_line_1": "3337 NE 76th Ave",
            "city": "Portland", "state": "OR", "postal_code": "97213",
            "phone": "971-801-5071", "email": "donnalieberson@gmail.com"
        },
        "guests": [
            {
                "first_name": "Donna", "last_name": "Lieberson",
                "phone": "971-801-5071", "email": "donnalieberson@gmail.com",
                "food_requests": "Does not eat lamb",
                "notes": "1st year at Paradise\nDoes not eat lamb\nShuttle Request - Casper\nHilton Garden Inn 1150 N. Popular St\nUA4658 @ 1:26pm"
            }
        ]
    },
    {
        "cabin": "Ranger",
        "household": {
            "name": "Robert Bobo",
            "address_line_1": "6601 Stone Crest Drive",
            "city": "Gillette", "state": "WY", "postal_code": "82717",
            "phone": "307-350-0166", "email": "hsotlj@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Robert", "last_name": "Bobo",
                "phone": "307-350-0166", "email": "hsotlj@yahoo.com",
                "notes": "4th year at Paradise\n9/9 is his 68th birthday\nDrive"
            }
        ]
    },
    {
        "cabin": "Little Sourdough",
        "household": {
            "name": "Sheldon & Phyllis Mutchnick",
            "address_line_1": "1917 Greenhurst Dr.",
            "city": "Henrico", "state": "VA", "postal_code": "23229",
            "phone": "804-971-3988", "email": "mutchs@verizon.net"
        },
        "guests": [
            {
                "first_name": "Sheldon", "last_name": "Mutchnick",
                "phone": "804-971-3988", "email": "mutchs@verizon.net",
                "medical_notes": "Sheldon had a stroke 15 years ago and needs people to speak to him slowly and clearly but not loudly so he can process. He mixes up words sometimes",
                "notes": "6th year at Paradise\nSheldon had a stroke 15 years ago and needs people to speak to him slowly and clearly but not loudly so he can process. He mixes up words sometimes\nDriving"
            },
            {
                "first_name": "Phyllis", "last_name": "Mutchnick",
                "phone": "804-839-7753", "email": "pmutchnick@gmail.com",
                "notes": "6th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Little Squaw",
        "household": {
            "name": "Georgiana Humes",
            "address_line_1": "240 Providence Street",
            "city": "Rehoboth", "state": "MA", "postal_code": "02769",
            "phone": "508-989-1117", "email": "waywardacres72@gmail.com"
        },
        "guests": [
            {
                "first_name": "Georgiana", "last_name": "Humes",
                "phone": "508-989-1117", "email": "waywardacres72@gmail.com",
                "food_requests": "Gluten Free",
                "notes": "1st year at Paradise\nGluten Free\nDriving"
            }
        ]
    },
    {
        "cabin": "Big Sourdough",
        "household": {
            "name": "Mark & Stephanie Wax",
            "address_line_1": "841 S Gaines St Unit 219",
            "city": "Portland", "state": "OR", "postal_code": "97239",
            "phone": "503-351-7592", "email": "1markwax@gmail.com"
        },
        "guests": [
            {
                "first_name": "Mark", "last_name": "Wax",
                "phone": "503-351-7592", "email": "1markwax@gmail.com",
                "allergies": "Allergic to bananas",
                "notes": "14th year at Paradise\nMark is allergic to bananas\nDriving"
            },
            {
                "first_name": "Stephanie", "last_name": "Wax",
                "phone": "503-351-7592", "email": "1markwax@gmail.com",
                "allergies": "Allergic to cilantro",
                "food_requests": "Does not eat beef",
                "notes": "14th year at Paradise\nStephanie is allergic to cilantro and does not eat beef\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Christi Vrban",
            "address_line_1": "6745 Catania Loop",
            "city": "Round Rock", "state": "TX", "postal_code": "78665",
            "phone": "713-502-1015", "email": "christi.vrban@gmail.com"
        },
        "guests": [
            {
                "first_name": "Christi", "last_name": "Vrban",
                "phone": "713-502-1015", "email": "christi.vrban@gmail.com",
                "notes": "Christi’s 4th year at Paradise\nReece & Rayne Boland’s family\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Raelynn Lynn Bucklin",
            "address_line_1": "23898 Timothy Ave",
            "city": "Murrietta", "state": "CA", "postal_code": "92562",
            "phone": "713-456-9057", "email": "lmtrehern@aol.com"
        },
        "guests": [
            {
                "first_name": "Raelynn (Lynn)", "last_name": "Bucklin",
                "phone": "713-456-9057", "email": "lmtrehern@aol.com",
                "medical_notes": "Has an allergic condition. Will carry an epi pen",
                "notes": "3rd year at Paradise\nHas an allergic condition. Will carry an epi pen.\nDriving"
            }
        ]
    },
    {
        "cabin": "Timberline",
        "household": {
            "name": "Joan Konecki",
            "address_line_1": "9583 W Albert Lane",
            "city": "Peoria", "state": "AZ", "postal_code": "85382",
            "phone": "623-693-6831", "email": "joankonecki@gmail.com"
        },
        "guests": [
            {
                "first_name": "Joan", "last_name": "Konecki",
                "phone": "623-693-6831", "email": "joankonecki@gmail.com",
                "notes": "2nd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Silver Dollar",
        "household": {
            "name": "Barry & Laura Rucker",
            "address_line_1": "1185 Humbug Way",
            "city": "Auburn", "state": "CA", "postal_code": "95603",
            "phone": "530-368-6251", "email": "rukshut@gmail.com"
        },
        "guests": [
            {
                "first_name": "Barry", "last_name": "Rucker",
                "phone": "530-368-6251", "email": "rukshut@gmail.com",
                "notes": "6th year at Paradise\nDriving"
            },
            {
                "first_name": "Laura", "last_name": "Rucker",
                "phone": "530-368-6251", "email": "rukshut@gmail.com",
                "allergies": "Allergy to hot peppers",
                "notes": "6th year at Paradise\nLaura has an allergy to hot peppers\nDriving"
            }
        ]
    },
    {
        "cabin": "Bear Paw",
        "household": {
            "name": "David Joslin",
            "address_line_1": "28709 Road P. 7",
            "city": "Dolores", "state": "CO", "postal_code": "81323",
            "phone": "970-739-1558", "email": "annstreettjoslin@gmail.com"
        },
        "guests": [
            {
                "first_name": "David", "last_name": "Joslin",
                "phone": "970-739-1558", "email": "annstreettjoslin@gmail.com",
                "notes": "7th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Bear Paw",
        "household": {
            "name": "Gerald Michaud",
            "address_line_1": "23 Prospect St",
            "city": "Waterville", "state": "ME", "postal_code": "04901",
            "phone": "207-333-7448", "email": "gerrynginger@roadrunner.com"
        },
        "guests": [
            {
                "first_name": "Gerald", "last_name": "Michaud",
                "phone": "207-333-7448", "email": "gerrynginger@roadrunner.com",
                "notes": "10th year at Paradise\nShuttle\nCasper UA5585 7:09pm"
            }
        ]
    },
    {
        "cabin": "Tensleep",
        "household": {
            "name": "Jim & Holly Popeo",
            "address_line_1": "191 Main Street",
            "address_line_2": "Unit 3",
            "city": "Gloucester", "state": "MA", "postal_code": "01930",
            "phone": "617-803-8446", "email": "jpopeo@comcast.net"
        },
        "guests": [
            {
                "first_name": "Jim", "last_name": "Popeo",
                "phone": "617-803-8446", "email": "jpopeo@comcast.net",
                "notes": "2nd year at Paradise\nDriving"
            },
            {
                "first_name": "Holly", "last_name": "Popeo",
                "phone": "617-803-8411", "email": "hpopeo@comcast.net",
                "notes": "2nd year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Shoshone",
        "household": {
            "name": "Donna Murphy",
            "address_line_1": "6742 E 6000 N Road",
            "city": "Grant Park", "state": "IL", "postal_code": "60940",
            "phone": "815-735-2431", "email": "donnamurphy2468@yahoo.com"
        },
        "guests": [
            {
                "first_name": "Donna", "last_name": "Murphy",
                "phone": "815-735-2431", "email": "donnamurphy2468@yahoo.com",
                "notes": "4th year at Paradise\nShuttle\nGillette UA4750 12:42pm\nGillette UA5682 1:19pm"
            }
        ]
    },
    {
        "cabin": "Shoshone",
        "household": {
            "name": "Kimber Janota",
            "address_line_1": "10843 Walnut Drive",
            "city": "St. John", "state": "IN", "postal_code": "46373",
            "phone": "708-341-2621", "email": ""
        },
        "guests": [
            {
                "first_name": "Kimber", "last_name": "Janota",
                "phone": "708-341-2621", "email": "",
                "allergies": "Allergic to Sulfad, IV Iodine, and Minocin",
                "medical_notes": "Kimber is a Type 2 Diabetic",
                "notes": "4th year at Paradise\nKimber is a Type 2 Diabetic. Allergic to Sulfad, IV Iodine, and Minocin\nShuttle\nGillette UA4750 12:42pm\nGillette UA5682 1:19pm"
            }
        ]
    },
    {
        "cabin": "Wagon Wheel",
        "household": {
            "name": "Beth Camp",
            "address_line_1": "246 Pikes Bluff Drive",
            "city": "Saint Simons Island", "state": "GA", "postal_code": "31522",
            "phone": "919-671-8975", "email": "bethaweber0630@gmail.com"
        },
        "guests": [
            {
                "first_name": "Beth", "last_name": "Camp",
                "phone": "919-671-8975", "email": "bethaweber0630@gmail.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan UA 5127 1:41 pm\nGillette UA 5672  1:06 pm"
            }
        ]
    },
    {
        "cabin": "Wagon Wheel",
        "household": {
            "name": "Melanie Barger",
            "address_line_1": "217 Stevens Road",
            "city": "Saint Simons Island", "state": "GA", "postal_code": "31522",
            "phone": "912-506-6261", "email": "melanie@hcrega.com"
        },
        "guests": [
            {
                "first_name": "Melanie", "last_name": "Barger",
                "phone": "912-506-6261", "email": "melanie@hcrega.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan UA 5127 1:41 pm\nGillette UA 5672  1:06 pm"
            }
        ]
    },
    {
        "cabin": "Virginian",
        "household": {
            "name": "David & Ann Wilkins",
            "address_line_1": "141 Holly Hock Lane",
            "city": "Ortonville", "state": "MI", "postal_code": "48462",
            "phone": "248-969-3900", "email": "annwilkins@charter.net"
        },
        "guests": [
            {
                "first_name": "David", "last_name": "Wilkins",
                "phone": "248-969-3900", "email": "annwilkins@charter.net",
                "notes": "1st year at Paradise\nShuttle\nSheridan UA 5127 1:40 pm\nSheridan UA 5040 2:20 pm"
            },
            {
                "first_name": "Ann", "last_name": "Wilkins",
                "phone": "248-568-1272", "email": "annwilkins@charter.net",
                "notes": "1st year at Paradise\nShuttle\nSheridan UA 5127 1:40 pm\nSheridan UA 5040 2:20 pm"
            }
        ]
    },
    {
        "cabin": "Ram's Head",
        "household": {
            "name": "Dennis & Terri McSweeney",
            "address_line_1": "7881 SE Spicewood Circle",
            "city": "Hobe Sound", "state": "FL", "postal_code": "33455",
            "phone": "516-695-8125", "email": "jr@jupiterrosellc.com"
        },
        "guests": [
            {
                "first_name": "Dennis", "last_name": "McSweeney",
                "phone": "516-695-8125", "email": "jr@jupiterrosellc.com",
                "notes": "1st year at Paradise\nDriving"
            },
            {
                "first_name": "Terri", "last_name": "McSweeney",
                "phone": "516-695-8125", "email": "jr@jupiterrosellc.com",
                "allergies": "Allergic to penicillin",
                "notes": "1st year at Paradise\nTerri is allergic to penicillin\nDriving"
            }
        ]
    },
    {
        "cabin": "Eagle's Nest",
        "household": {
            "name": "Jim & Lynne Starley",
            "address_line_1": "1694 Marinet Lane",
            "city": "Ogden", "state": "UT", "postal_code": "84403",
            "phone": "801-725-5878", "email": "jwstarley@comcast.net"
        },
        "guests": [
            {
                "first_name": "Jim", "last_name": "Starley",
                "phone": "801-725-5878", "email": "jwstarley@comcast.net",
                "notes": "1st year at Paradise\nDriving"
            },
            {
                "first_name": "Lynne", "last_name": "Starley",
                "phone": "801-725-5878", "email": "jwstarley@comcast.net",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Trapper",
        "household": {
            "name": "Candia Rizzo",
            "address_line_1": "1018 Saint Anne Street",
            "city": "Sparta", "state": "WI", "postal_code": "54656",
            "phone": "603-490-5235", "email": "crizzo9907@gmail.com"
        },
        "guests": [
            {
                "first_name": "Candia", "last_name": "Rizzo",
                "phone": "603-490-5235", "email": "crizzo9907@gmail.com",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Trapper",
        "household": {
            "name": "Kirsti Trygstad",
            "address_line_1": "10452 Impala Ave.",
            "city": "Sparta", "state": "WI", "postal_code": "54656",
            "phone": "612-817-4017", "email": "ktry.gstad@centurytel.net"
        },
        "guests": [
            {
                "first_name": "Kirsti", "last_name": "Trygstad",
                "phone": "612-817-4017", "email": "ktry.gstad@centurytel.net",
                "notes": "1st year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Wapiti",
        "household": {
            "name": "Keith & Debbie Vranesh",
            "address_line_1": "152 Monte Vista Ave",
            "city": "Costa Mesa", "state": "CA", "postal_code": "92627",
            "phone": "714-585-0186", "email": "debzmail@msn.com"
        },
        "guests": [
            {
                "first_name": "Keith", "last_name": "Vranesh",
                "phone": "714-585-0186", "email": "debzmail@msn.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan - returning rental car so open to when pick them up\nHilton Hampton Inn - Sheridan 980 Sible Circle"
            },
            {
                "first_name": "Debbie", "last_name": "Vranesh",
                "phone": "714-585-0186", "email": "debzmail@msn.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan - returning rental car so open to when pick them up\nHilton Hampton Inn - Sheridan 980 Sible Circle"
            }
        ]
    },
    {
        "cabin": "Wapiti",
        "household": {
            "name": "Dale & Katy Johnson",
            "address_line_1": "1818 Vai Ladera",
            "city": "Fallbrook", "state": "CA", "postal_code": "92028",
            "phone": "858-442-0399", "email": "katymj@icloud.com"
        },
        "guests": [
            {
                "first_name": "Dale", "last_name": "Johnson",
                "phone": "858-442-0399", "email": "katymj@icloud.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan - returning rental car so open to when pick them up\nHilton Hampton Inn - Sheridan 980 Sible Circle"
            },
            {
                "first_name": "Katy", "last_name": "Johnson",
                "phone": "858-442-0399", "email": "katymj@icloud.com",
                "notes": "1st year at Paradise\nShuttle\nSheridan - returning rental car so open to when pick them up\nHilton Hampton Inn - Sheridan 980 Sible Circle"
            }
        ]
    },
    {
        "cabin": "Bigfoot",
        "household": {
            "name": "Ryan & Cindy Porter",
            "address_line_1": "22872 Via Cordova",
            "city": "Dana Point", "state": "CA", "postal_code": "92625",
            "phone": "949-933-8695", "email": "ryan@grsrelo.com"
        },
        "guests": [
            {
                "first_name": "Ryan", "last_name": "Porter",
                "phone": "949-933-8695", "email": "ryan@grsrelo.com",
                "notes": "Ryan’s first year at Paradise\nDriving"
            },
            {
                "first_name": "Cindy", "last_name": "Porter",
                "phone": "949-933-8695", "email": "ryan@grsrelo.com",
                "notes": "Cindy’s 17th year at Paradise\nDriving"
            }
        ]
    },
    {
        "cabin": "Black Powder",
        "household": {
            "name": "Dodi Ryder",
            "address_line_1": "4723 Suffolk Court",
            "city": "Ventura", "state": "CA", "postal_code": "93003",
            "phone": "805-812-2045", "email": "dorisryder25@gmail.com"
        },
        "guests": [
            {
                "first_name": "Dodi", "last_name": "Ryder",
                "phone": "805-812-2045", "email": "dorisryder25@gmail.com",
                "notes": "Shuttle\nSheridan Ramada Plaza"
            }
        ]
    }
]

@transaction.atomic
def run_import():
    print("Setting up cabins...")
    # Update or create all 18 standard cabins
    cabin_map = {}
    for cdata in CABINS_DATA:
        cabin, _ = Cabin.objects.update_or_create(
            name=cdata["name"],
            defaults={
                "capacity": cdata["capacity"],
                "sort_order": cdata["sort_order"],
                "status": Cabin.CabinStatus.AVAILABLE,
                "is_active": True,
            }
        )
        cabin_map[cdata["name"]] = cabin
    
    # Also handle old "Silver Doller" or "Test Cabin" if present
    Cabin.objects.filter(name="Silver Doller").delete()
    Cabin.objects.filter(name="Test Cabin").delete()

    print(f"Total cabins ready: {Cabin.objects.count()}")

    def import_week_data(dataset, arrival_dt, departure_dt, week_name):
        print(f"\nImporting {week_name} ({arrival_dt} to {departure_dt})...")
        guest_count_total = 0
        for entry in dataset:
            cabin_name = entry["cabin"]
            cabin = cabin_map[cabin_name]
            hdata = entry["household"]
            guests_data = entry["guests"]

            # Create or get primary contact client
            import re
            first_guest = guests_data[0]
            first_notes = first_guest.get("notes", "")
            match_yr = re.search(r"(\d+)(?:st|nd|rd|th)?\s+year", first_notes, re.IGNORECASE)
            yr_return = int(match_yr.group(1)) if match_yr else None

            primary_client, _ = Client.objects.get_or_create(
                first_name=first_guest["first_name"],
                last_name=first_guest["last_name"],
                defaults={
                    "phone": first_guest.get("phone") or hdata.get("phone", ""),
                    "email": first_guest.get("email") or hdata.get("email", ""),
                    "dietary_notes": first_guest.get("food_requests", ""),
                    "medical_notes": first_guest.get("medical_notes", ""),
                    "general_notes": first_guest.get("notes", ""),
                    "years_return": yr_return,
                }
            )
            if yr_return and not primary_client.years_return:
                primary_client.years_return = yr_return
                primary_client.save()

            # Create or get household
            household, _ = Household.objects.get_or_create(
                name=hdata["name"],
                defaults={
                    "primary_contact": primary_client,
                    "address_line_1": hdata.get("address_line_1", ""),
                    "address_line_2": hdata.get("address_line_2", ""),
                    "city": hdata.get("city", ""),
                    "state": hdata.get("state", ""),
                    "postal_code": hdata.get("postal_code", ""),
                    "country": hdata.get("country", "USA"),
                    "years_return": yr_return,
                    "is_active": True,
                }
            )
            if yr_return and not household.years_return:
                household.years_return = yr_return
                household.save()

            # Create Reservation
            res_name = f"{hdata['name']} - {cabin_name}"
            reservation, _ = Reservation.objects.get_or_create(
                reservation_name=res_name,
                arrival_date=arrival_dt,
                departure_date=departure_dt,
                defaults={
                    "reservation_type": Reservation.ReservationType.GUEST_STAY,
                    "status": Reservation.ReservationStatus.CONFIRMED,
                    "primary_contact": primary_client,
                    "household": household,
                    "adult_count": len(guests_data),
                    "guest_count": len(guests_data),
                }
            )

            # Assign cabin to reservation
            ReservationCabin.objects.get_or_create(
                reservation=reservation,
                cabin=cabin,
                arrival_date=arrival_dt,
                departure_date=departure_dt
            )

            for gdata in guests_data:
                client, _ = Client.objects.get_or_create(
                    first_name=gdata["first_name"],
                    last_name=gdata["last_name"],
                    defaults={
                        "phone": gdata.get("phone") or hdata.get("phone", ""),
                        "email": gdata.get("email") or hdata.get("email", ""),
                        "dietary_notes": gdata.get("food_requests", ""),
                        "medical_notes": gdata.get("medical_notes", ""),
                        "general_notes": gdata.get("notes", ""),
                    }
                )

                HouseholdMember.objects.get_or_create(
                    household=household,
                    client=client,
                    defaults={
                        "is_primary_contact": (client == primary_client),
                        "relationship": HouseholdMember.Relationship.SELF if client == primary_client else HouseholdMember.Relationship.OTHER,
                    }
                )

                # ReservationGuest
                ReservationGuest.objects.update_or_create(
                    reservation=reservation,
                    client=client,
                    defaults={
                        "cabin": cabin,
                        "allergies": gdata.get("allergies", ""),
                        "food_requests": gdata.get("food_requests", ""),
                        "medical_notes": gdata.get("medical_notes", ""),
                        "notes": gdata.get("notes", ""),
                        "is_riding": True,
                    }
                )
                guest_count_total += 1

        print(f"Total guests imported for {week_name}: {guest_count_total}")

    import_week_data(DATA_WEEK1, date(2026, 8, 30), date(2026, 9, 6), "August 30 - September 6, 2026")
    import_week_data(DATA_WEEK2, date(2026, 9, 6), date(2026, 9, 13), "September 6 - 13, 2026")

if __name__ == "__main__":
    run_import()
    print("\nImport completed successfully!")
