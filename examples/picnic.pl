% Picnic example from the Logic Computing 4 slides (propositional logic slide).
% The slide's rule  (D & (F v (~G & E))) => H  is not Horn because of the "or"
% and the "not", so it is split into two rules and "not raining" (G) is
% replaced by its own atom "raining".
car_has_gas.
have_money.
raining.
have_umbrella.

get_to_store :- car_has_gas.                    % A => B
have_food    :- get_to_store, have_money.       % (B & C) => D
picnic       :- have_food, sun_shining.         % D & F => H
picnic       :- have_food, raining, have_umbrella.  % D & ~G & E => H

?- picnic.        % provable -> wff UNSAT -> Prolog answers "yes"
