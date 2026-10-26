bank_acct_over_2000.
no_debt.
seats_available.
room_available.

has_enough_money :- bank_acct_over_2000, no_debt.
book_flights :- has_enough_money, seats_available.
book_hotel :- has_enough_money, room_available.
vacation :- book_flights, book_hotel.

?- vacation.