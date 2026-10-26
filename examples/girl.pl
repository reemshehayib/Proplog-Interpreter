% Example 1 from https://web.stanford.edu/class/cs227/Lectures/lec08a.pdf

first_grade.
female.

child :- first_grade.
boy :- child, male.
child :- kindergarten.
girl :- child, female.

?- girl.